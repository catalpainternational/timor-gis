"""Human-readable changeset for a proposed sync, and the review set that needs
domain sign-off before the crosswalk is trusted.

Confident rows (exact/strong name + overlap) are summarised by count; the report
spends its words on what a reviewer must actually decide: new entities, removed
entities, admin-post restructuring, and low-confidence pairings.
"""

from __future__ import annotations

from .matching import score_pair

LOW_CONFIDENCE = 0.70
ECHO_THRESHOLD = 0.85


def build_report(rows, post_lookup, removed, canon_sucos) -> str:
    matched = [r for r in rows if r.status == "matched"]
    new = [r for r in rows if r.status == "new"]
    lowconf = sorted((r for r in matched if float(r.score) < LOW_CONFIDENCE), key=lambda r: r.score)
    new_posts = [p for p in post_lookup.values() if p["status"] == "new"]

    # removed canonicals that a new suco name-echoes (possible rename, not new/removed)
    echoes = []
    for r in new:
        for c in removed:
            if score_pair(r.provider_name, canon_sucos[c]["SUCONAME"]) >= ECHO_THRESHOLD:
                echoes.append((r, c))
    echoed = {c for _, c in echoes}

    out = ["# Sync changeset (proposed)", ""]
    out.append(f"- matched: **{len(matched)}**  |  new: **{len(new)}**  |  removed: **{len(removed)}**")
    out.append(f"- new admin posts: **{len(new_posts)}**")
    out.append("")

    out.append("## New admin posts (minted SUBDSTCODE)")
    for p in sorted(new_posts, key=lambda p: p["subdstcode"]):
        out.append(f"- {p['distname']} / **{p['intl_post']}** -> {p['subdstcode']}")
    out.append("")

    out.append("## New sucos (minted SUCOCODE)")
    for r in sorted(new, key=lambda r: r.canonical_pcode):
        out.append(f"- {r.provider_name} ({r.distname}/{r.subdistrct}) -> {r.canonical_pcode}")
    out.append("")

    out.append("## REVIEW: low-confidence matches (name disagrees with geometry pairing)")
    for r in lowconf:
        out.append(
            f"- [{r.distname}/{r.subdistrct}] INTL **{r.provider_name}** -> canonical "
            f"**{r.canonical_name}** ({r.canonical_pcode}), name~{r.score}"
        )
    out.append("")

    out.append("## REVIEW: removed canonical sucos")
    for c in removed:
        s = canon_sucos[c]
        tag = " (echoed by a 'new' suco -> likely rename)" if c in echoed else " (no echo -> merged away?)"
        out.append(f"- **{s['SUCONAME']}** ({s['DISTNAME']}/{s['SUBDISTRCT']}, {c}){tag}")
    for r, c in echoes:
        out.append(f"    - echo: new **{r.provider_name}** ~ removed **{canon_sucos[c]['SUCONAME']}**")
    out.append("")
    return "\n".join(out)
