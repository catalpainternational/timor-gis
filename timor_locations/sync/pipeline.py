"""End-to-end provider sync: ingest -> reconcile (municipality/post/suco) ->
geographic validation -> emit importer gpkg/csv.

The provider is treated as authoritative for *structure, geometry, names and
parent relationships*; the canonical dataset contributes only stable pcodes, via
the crosswalk, so downstream keys never move. Anything the provider introduces
gets a freshly minted canonical code (see :mod:`.codes`).

Geometry note: the importer derives admin-post/municipality polygons by unioning
suco geometries, so only the suco layer's geometry is emitted. The admin
hierarchy travels as explicit CSV columns, which is what lets a re-parented suco
keep its code while pointing ``SUBDSTCODE`` at its true current post.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from django.contrib.gis.gdal import DataSource, OGRGeometry, SpatialReference

from .crosswalk import CrosswalkRow
from .matching import build_candidates, match_one, score_pair
from .normalize import normalize

WGS84 = 4326


@dataclass
class Feature:
    code: str
    name: str
    post: str
    municipality: str
    suco: str
    geom_src: OGRGeometry  # in the provider's native CRS, for containment checks


def read_layer(source_dir: str, spec) -> list[Feature]:
    ds = DataSource(str(Path(source_dir) / spec.layer_file))
    layer = ds[0]
    fm = spec.fields
    out = []
    for feat in layer:
        out.append(
            Feature(
                code=str(feat.get(fm["code"])) if "code" in fm else "",
                name=str(feat.get(fm["name"])) if "name" in fm else "",
                post=str(feat.get(fm["post"])) if "post" in fm else "",
                municipality=str(feat.get(fm["municipality"])) if "municipality" in fm else "",
                suco=str(feat.get(fm["suco"])) if "suco" in fm else "",
                geom_src=feat.geom.clone(),
            )
        )
    return out


def to_multipolygon_4326(geom_src: OGRGeometry) -> OGRGeometry:
    g = geom_src.clone()
    g.transform(SpatialReference(WGS84))
    if g.geom_type.name == "Polygon":
        mp = OGRGeometry("MULTIPOLYGON", SpatialReference(WGS84))
        mp.add(g)
        g = mp
    return g


# --- canonical registries (from the current importer csv) -----------------------


def load_canonical(csv_path: str):
    """Returns (sucos_by_pcode, posts_by_subdst, muni_by_distcode, muni_by_name)."""
    sucos, posts, muni_dc, muni_nm = {}, {}, {}, {}
    with open(csv_path) as fh:
        for r in csv.DictReader(fh):
            sucos[r["SUCOCODE"]] = r
            posts.setdefault(
                r["SUBDSTCODE"],
                {"subdstcode": r["SUBDSTCODE"], "name": r["SUBDISTRCT"], "distcode": r["DISTCODE"]},
            )
            muni_dc.setdefault(
                r["DISTCODE"], {"distcode": r["DISTCODE"], "name": r["DISTNAME"], "region": r["REGION"]}
            )
            muni_nm.setdefault(normalize(r["DISTNAME"]), r["DISTCODE"])
    return sucos, posts, muni_dc, muni_nm


# --- geometric reconciliation ---------------------------------------------------


OVERLAP_WEIGHT = 0.4  # geometry weight relative to name; name stays dominant
MATCH_FLOOR = 0.55  # minimum combined score for a confident pair


def combined_match(intl_sucos, canon_sucos, canonical_gpkg):
    """Entity-resolve INTL sucos to canonical sucos by *mutual best* of a combined
    name+overlap score.

    ``combined = name_similarity + OVERLAP_WEIGHT * (intersection / canonical_area)``

    Name dominates -- so a respelled suco beats a higher-overlapping neighbour of a
    different name (kills boundary-shift "swaps"). Overlap disambiguates duplicate
    names within a municipality (two ``Samalari`` -> the right one), confirms
    respellings, and lets split children fail mutuality (the parent's continuation
    wins it) so they fall through to *new*.

    Returns (matched: {intl_code -> canon_pcode}, removed: [canon_pcode]).
    """
    ds = DataSource(str(canonical_gpkg))
    layer = ds[0]
    canon_geom = {str(feat.get("SUCOCODE")): feat.geom.geos for feat in layer}
    canon = []
    for pcode, name in ((c, canon_sucos[c]["SUCONAME"]) for c in canon_sucos):
        g = canon_geom.get(pcode)
        if g is None:
            continue
        canon.append((pcode, name, g, g.area, g.extent))

    intl = []
    for f in intl_sucos:
        g = f.geom_src.clone()
        g.transform(SpatialReference(WGS84))
        gg = g.geos
        intl.append((f.code, f.name, gg, gg.extent))

    def bbox_hit(a, b):
        return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

    # score every overlapping (intl, canon) pair once
    pair_score: dict[tuple[str, str], float] = {}
    for icode, iname, ig, iext in intl:
        for pcode, cname, cg, carea, cext in canon:
            if not bbox_hit(iext, cext) or not ig.intersects(cg):
                continue
            inter = ig.intersection(cg).area
            if inter <= 0:
                continue
            score = score_pair(iname, cname) + OVERLAP_WEIGHT * (inter / carea if carea else 0.0)
            pair_score[(icode, pcode)] = score

    # global greedy one-to-one assignment: take the highest-scoring pair whose
    # endpoints are both still free, repeat. Exact-name pairs (name==1.0) sort
    # above overlap-only neighbours, so identical names lock to each other first
    # and duplicate names within a municipality are split by overlap.
    matched = {}
    taken_canon: set[str] = set()
    for (icode, pcode), s in sorted(pair_score.items(), key=lambda kv: kv[1], reverse=True):
        if s < MATCH_FLOOR:
            break
        if icode in matched or pcode in taken_canon:
            continue
        matched[icode] = pcode
        taken_canon.add(pcode)
    removed = [c for c in canon_sucos if c not in taken_canon]
    return matched, removed


# --- reconciliation -------------------------------------------------------------


POST_MATCH_FLOOR = 0.80


def reconcile_posts(intl_posts, canon_posts, muni_nm, muni_dc, allocator):
    """Map each INTL admin post to a canonical SUBDSTCODE (existing or minted),
    *one-to-one* within a municipality.

    One-to-one matters: when a post splits (Quelicai -> Quelicai Antigo + Matebian,
    Hatolia -> Hatulia A + Hatulia B), exactly one child inherits the old code and
    the rest are minted as new posts -- so identity isn't decided by which child's
    name happens to resemble the parent's.

    Returns a dict keyed by (normalized municipality, normalized post) ->
    {subdstcode, subdistrct, intl_post, distcode, distname, region, status}.
    """
    # resolve municipality up front
    dc_of = {}
    for f in intl_posts:
        dc = muni_nm.get(normalize(f.municipality))
        if dc is None:
            raise ValueError(f"INTL municipality {f.municipality!r} has no canonical match")
        dc_of[f.code] = dc

    # greedy one-to-one name match within municipality
    pairs = []
    for f in intl_posts:
        for ccode, p in canon_posts.items():
            if p["distcode"] != dc_of[f.code]:
                continue
            pairs.append((score_pair(f.name, p["name"]), f.code, ccode))
    pairs.sort(reverse=True)
    matched_canon, matched_intl = set(), {}
    for score, icode, ccode in pairs:
        if score < POST_MATCH_FLOOR or icode in matched_intl or ccode in matched_canon:
            continue
        matched_intl[icode] = ccode
        matched_canon.add(ccode)

    out = {}
    for f in intl_posts:
        dc = dc_of[f.code]
        muni = muni_dc[dc]
        ccode = matched_intl.get(f.code)
        if ccode is not None:
            code, name, status = ccode, canon_posts[ccode]["name"], "matched"
        else:
            code = str(allocator.mint_post(int(dc)))
            name, status = f.name, "new"
        out[(normalize(f.municipality), normalize(f.name))] = {
            "subdstcode": code,
            "subdistrct": name,
            "intl_post": f.name,
            "distcode": muni["distcode"],
            "distname": muni["name"],
            "region": muni["region"],
            "status": status,
        }
    return out


def apply_overrides(geo_matched, overrides):
    """Fold reviewed human decisions into the geometric pairing.

    ``overrides`` rows (provider_code -> canonical_pcode / status / name) are the
    durable record of review: a swap re-pairs both sides, a rename keeps a pcode
    under a new name, a 'new' forces an entity to be minted. Honoured verbatim on
    every re-run, so manual judgement is never silently recomputed away.

    Returns (matched, name_override, status_override).
    """
    matched = dict(geo_matched)
    name_override, status_override = {}, {}
    for ov in overrides:
        pc = ov["provider_code"]
        status_override[pc] = ov["status"]
        if ov["status"] == "new" or not ov["canonical_pcode"]:
            matched.pop(pc, None)
            continue
        # free any other provider currently holding this canonical pcode
        for other, canon in list(matched.items()):
            if canon == ov["canonical_pcode"] and other != pc:
                matched.pop(other)
        matched[pc] = ov["canonical_pcode"]
        if ov.get("canonical_name"):
            name_override[pc] = ov["canonical_name"]
    return matched, name_override, status_override


def reconcile_sucos(
    intl_sucos,
    canon_sucos,
    post_lookup,
    allocator,
    provider_key,
    geo_matched,
    name_override=None,
    status_override=None,
):
    """Build suco crosswalk rows. Identity comes from ``geo_matched``
    (intl_code -> canonical_pcode, by polygon overlap); a name-similarity score is
    recorded only as evidence/label. Geometrically-unmatched sucos are new and get
    a freshly minted code under their reconciled admin post."""
    name_override = name_override or {}
    status_override = status_override or {}
    cand_rows = [{"code": c, "name": s["SUCONAME"], "mun": s["DISTNAME"]} for c, s in canon_sucos.items()]
    cands = build_candidates(cand_rows, pcode="code", name="name", parent="mun")
    rows: list[CrosswalkRow] = []
    for f in intl_sucos:
        post = post_lookup.get((normalize(f.municipality), normalize(f.post)))
        if post is None:
            raise ValueError(f"Suco {f.name!r}: no reconciled post for {f.municipality}/{f.post}")
        ev = match_one(f.code, f.name, f.municipality, cands)  # name evidence only
        pcode = geo_matched.get(f.code)
        if pcode is not None:
            cname = name_override.get(f.code, canon_sucos[pcode]["SUCONAME"])
            status = status_override.get(f.code, "matched")
            # flag matched pairs whose names disagree -- a respelling or a possible mis-pair
            note = "" if ev.pcode == pcode else f"name~{ev.canonical_name or '?'}({ev.score:.2f}); geom-paired"
        else:
            pcode = str(allocator.mint_suco(int(post["subdstcode"])))
            cname, status, note = f.name, status_override.get(f.code, "new"), ""
        rows.append(
            CrosswalkRow(
                provider=provider_key,
                provider_code=f.code,
                provider_name=f.name,
                provider_post=f.post,
                provider_mun=f.municipality,
                canonical_pcode=pcode,
                canonical_name=cname,
                subdstcode=post["subdstcode"],
                distcode=post["distcode"],
                distname=post["distname"],
                subdistrct=post["subdistrct"],
                region=post["region"],
                status=status,
                score=f"{ev.score:.2f}",
                note=note,
            )
        )
    return rows


# --- geographic guard -----------------------------------------------------------


def validate_containment(intl_sucos, intl_posts):
    """Every suco's representative point must lie inside its coded post polygon.

    Works in the provider's native CRS (planar) where both layers live. Returns a
    list of (suco, municipality, coded_post, actual_post) offenders; empty == clean.
    """
    posts = [(normalize(p.municipality), normalize(p.name), p.name, p.geom_src.geos) for p in intl_posts]
    offenders = []
    for s in intl_sucos:
        rep = s.geom_src.geos.point_on_surface
        coded = (normalize(s.municipality), normalize(s.post))
        container = next(((mn, pn, label) for mn, pn, label, g in posts if g.contains(rep)), None)
        if container is None or (container[0], container[1]) != coded:
            offenders.append((s.name, s.municipality, s.post, container[2] if container else "OUTSIDE"))
    return offenders


# --- INTL-keyed emit (both tracks now use the provider's New*Cod scheme) ---------


def emit_sucos_intl(source_dir, spec, out_csv, out_gpkg):
    """Emit sukus.gpkg + sukus.csv keyed on the INTL scheme (NewSucoCod), directly
    from the provider suco layer -- the same shape as the aldeia emit, no legacy
    code involved. gpkg carries SUCONAME/SUBDSTCODE/DISTCODE/SUCOCODE/REGION (now
    string codes) + geometry; csv adds DISTNAME/SUBDISTRCT names for the importer.

    REGION is retained as an (empty) column only because the importer's csv loop
    unpacks 7 fields; it is not stored on any model.
    """
    import csv as _csv
    import json
    import subprocess
    import tempfile
    from pathlib import Path

    layer = DataSource(str(Path(source_dir) / spec.layer_file))[0]
    rows, features = [], []
    for feat in layer:
        suco, sucocode = str(feat.get("SUCO")), str(feat.get("NewSucoCod"))
        post, subdst = str(feat.get("P_ADMIN")), str(feat.get("NewPostAdC"))
        mun, dist = str(feat.get("MUNICIPIO")), str(feat.get("NewMunCode"))
        rows.append([suco, subdst, dist, mun, post, sucocode, ""])
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "SUCONAME": suco,
                    "SUBDSTCODE": subdst,
                    "DISTCODE": dist,
                    "SUCOCODE": sucocode,
                    "REGION": "",
                },
                "geometry": json.loads(to_multipolygon_4326(feat.geom).json),
            }
        )

    with open(out_csv, "w", newline="") as fh:
        w = _csv.writer(fh)
        w.writerow(["SUCONAME", "SUBDSTCODE", "DISTCODE", "DISTNAME", "SUBDISTRCT", "SUCOCODE", "REGION"])
        w.writerows(sorted(rows, key=lambda r: r[5]))

    fc = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
        "features": features,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as tmp:
        json.dump(fc, tmp)
        tmp_path = tmp.name
    Path(out_gpkg).unlink(missing_ok=True)
    try:
        subprocess.run(
            [
                "ogr2ogr",
                "-f",
                "GPKG",
                str(out_gpkg),
                tmp_path,
                "-nln",
                "sukus",
                "-nlt",
                "MULTIPOLYGON",
                "-lco",
                "GEOMETRY_NAME=geom",
                "-a_srs",
                "EPSG:4326",
            ],
            check=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# --- aldeia track (already on the INTL "new" code scheme) -----------------------

ALDEIA_FIELDS = ["ALDEIA", "SUCO", "P_ADMIN", "MUNICIPIO", "NewAldCode", "NewSucoCod", "NewPostAdC", "NewMunCode"]


def emit_aldeias(source_dir, spec, out_path):
    """Emit aldeias_2022.gpkg from the INTL aldeia layer: reproject to EPSG:4326,
    promote to MULTIPOLYGON, keep the importer's fields. NewAldCode is adopted
    verbatim -- the data is already on the INTL scheme, so there is no remapping
    and no legacy code is ever involved."""
    import subprocess

    out_path = Path(out_path)
    out_path.unlink(missing_ok=True)
    src = str(Path(source_dir) / spec.layer_file)
    subprocess.run(
        [
            "ogr2ogr",
            "-f",
            "GPKG",
            str(out_path),
            src,
            "-t_srs",
            "EPSG:4326",
            "-nlt",
            "MULTIPOLYGON",
            "-nln",
            "aldeias_2022",
            "-lco",
            "GEOMETRY_NAME=geom",
            "-select",
            ",".join(ALDEIA_FIELDS),
        ],
        check=True,
    )
