"""Reconcile a provider's boundary drop into the canonical importer data.

Two phases, gated by human review of the crosswalk:

    # 1. propose: read provider shapefiles, reconcile against the current
    #    importer csv/gpkg, write the proposed crosswalk + a changeset report.
    manage.py sync_provider_geo intl2024 --source /path/to/shapefiles --propose

    # ...review crosswalk/suco_crosswalk.csv, fix any flagged rows...

    # 2. apply: regenerate sukus.gpkg + sukus.csv from the reviewed crosswalk.
    manage.py sync_provider_geo intl2024 --source /path/to/shapefiles --apply

``--apply`` runs the geographic guard first (every suco must sit inside its coded
admin-post polygon) and aborts on any violation. Identity comes from polygon
overlap, not names, so respellings / re-parentings / duplicate names don't move a
stable pcode. See :mod:`timor_locations.sync.pipeline`.
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from timor_locations.sync import crosswalk as xwalk
from timor_locations.sync import pipeline as P
from timor_locations.sync import report as report_mod
from timor_locations.sync.adapters import PROVIDERS
from timor_locations.sync.codes import CodeAllocator

DATA = Path(__file__).resolve().parents[2] / "data"
CSV = DATA / "sukus.csv"
GPKG = DATA / "sukus.gpkg"
XWALK = DATA / "crosswalk" / "suco_crosswalk.csv"
OVERRIDES = DATA / "crosswalk" / "suco_overrides.csv"
REPORT = DATA / "crosswalk" / "sync_report.md"


def _load_overrides(provider_key):
    import csv

    if not OVERRIDES.exists():
        return []
    with OVERRIDES.open() as fh:
        return [r for r in csv.DictReader(fh) if r["provider"] == provider_key]


class Command(BaseCommand):
    help = "Reconcile a provider boundary drop into the canonical suco data."

    def add_arguments(self, parser):
        parser.add_argument("provider", choices=sorted(PROVIDERS), help="provider key (see adapters.py)")
        parser.add_argument("--source", required=True, help="directory holding the provider shapefiles")
        parser.add_argument("--propose", action="store_true", help="write crosswalk + report only")
        parser.add_argument("--apply", action="store_true", help="emit sukus.gpkg + sukus.csv")

    def handle(self, *args, **opts):
        if not (opts["propose"] or opts["apply"]):
            raise CommandError("choose --propose and/or --apply")
        provider = PROVIDERS[opts["provider"]]
        src = opts["source"]

        self.stdout.write("Reading provider layers...")
        intl_posts = P.read_layer(src, provider.levels["post"])
        intl_sucos = P.read_layer(src, provider.levels["suco"])
        canon_sucos, canon_posts, muni_dc, muni_nm = P.load_canonical(CSV)

        allocator = CodeAllocator({int(c) for c in canon_sucos} | {int(c) for c in canon_posts})
        post_lookup = P.reconcile_posts(intl_posts, canon_posts, muni_nm, muni_dc, allocator)

        self.stdout.write("Geographic guard: checking suco-in-post containment...")
        offenders = P.validate_containment(intl_sucos, intl_posts)
        if offenders:
            for name, mun, coded, actual in offenders[:50]:
                self.stderr.write(f"  {name} [{mun}] coded->{coded} but sits in {actual}")
            raise CommandError(f"{len(offenders)} suco(s) outside their coded admin post; aborting.")

        self.stdout.write("Matching sucos by name+overlap (mutual/global)...")
        matched, removed = P.combined_match(intl_sucos, canon_sucos, GPKG)
        overrides = _load_overrides(provider.key)
        matched, name_override, status_override = P.apply_overrides(matched, overrides)
        removed = [c for c in canon_sucos if c not in set(matched.values())]
        if overrides:
            self.stdout.write(f"Applied {len(overrides)} reviewed override(s).")
        rows = P.reconcile_sucos(
            intl_sucos,
            canon_sucos,
            post_lookup,
            allocator,
            provider.key,
            matched,
            name_override,
            status_override,
        )

        counts = {s: sum(r.status == s for r in rows) for s in ("matched", "new")}
        self.stdout.write(
            self.style.SUCCESS(
                f"matched={counts['matched']} new={counts['new']} removed={len(removed)} "
                f"new_posts={sum(p['status'] == 'new' for p in post_lookup.values())}"
            )
        )

        if opts["propose"]:
            xwalk.save(XWALK, rows)
            REPORT.write_text(report_mod.build_report(rows, post_lookup, removed, canon_sucos))
            self.stdout.write(self.style.SUCCESS(f"Wrote {XWALK}\nWrote {REPORT}"))

        if opts["apply"]:
            P.emit_csv(rows, CSV)
            P.emit_gpkg(rows, intl_sucos, GPKG)
            self.stdout.write(self.style.SUCCESS(f"Emitted {CSV} and {GPKG} ({len(rows)} sucos)"))
