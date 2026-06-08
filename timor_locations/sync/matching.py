"""Match provider features to canonical entities, hierarchy-scoped.

A match is resolved in three tiers, strongest first:

1. **Crosswalk** -- ``(provider, provider_code)`` already recorded. Deterministic;
   no guessing on re-runs. This is what makes repeat drops cheap.
2. **Exact normalized name** within the same parent (municipality for sucos).
3. **Fuzzy** -- best ``difflib`` ratio over the conservative and phonetic keys,
   within the same parent, above ``AUTO_THRESHOLD``. Anything between
   ``REVIEW_THRESHOLD`` and ``AUTO_THRESHOLD`` is surfaced for human review;
   below ``REVIEW_THRESHOLD`` the feature is treated as new.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from .normalize import normalize, phonetic_key

AUTO_THRESHOLD = 0.86
REVIEW_THRESHOLD = 0.66


@dataclass
class Candidate:
    """A canonical entity available to match against, scoped to a parent."""

    pcode: str
    name: str
    parent_key: str  # normalized parent name (municipality) for scoping
    norm: str
    phon: str


@dataclass
class MatchResult:
    provider_code: str
    provider_name: str
    parent_key: str
    pcode: str | None
    canonical_name: str | None
    score: float
    tier: str  # "crosswalk" | "exact" | "fuzzy" | "review" | "new"


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def score_pair(name_a: str, name_b: str) -> float:
    """Combined similarity: best of the conservative and phonetic keys."""
    return max(
        _ratio(normalize(name_a), normalize(name_b)),
        _ratio(phonetic_key(name_a), phonetic_key(name_b)),
    )


def build_candidates(rows: list[dict], *, pcode: str, name: str, parent: str) -> list[Candidate]:
    out = []
    for r in rows:
        out.append(
            Candidate(
                pcode=str(r[pcode]),
                name=r[name],
                parent_key=normalize(r[parent]),
                norm=normalize(r[name]),
                phon=phonetic_key(r[name]),
            )
        )
    return out


def match_one(
    provider_code: str,
    provider_name: str,
    parent_name: str,
    candidates: list[Candidate],
    *,
    crosswalk_pcode: str | None = None,
) -> MatchResult:
    parent_key = normalize(parent_name)
    if crosswalk_pcode is not None:
        canon = next((c for c in candidates if c.pcode == crosswalk_pcode), None)
        return MatchResult(
            provider_code,
            provider_name,
            parent_key,
            crosswalk_pcode,
            canon.name if canon else None,
            1.0,
            "crosswalk",
        )

    scoped = [c for c in candidates if c.parent_key == parent_key] or candidates
    pname_norm = normalize(provider_name)
    pname_phon = phonetic_key(provider_name)

    exact = [c for c in scoped if c.norm == pname_norm]
    if exact:
        c = exact[0]
        return MatchResult(provider_code, provider_name, parent_key, c.pcode, c.name, 1.0, "exact")

    best, best_score = None, 0.0
    for c in scoped:
        s = max(_ratio(pname_norm, c.norm), _ratio(pname_phon, c.phon))
        if s > best_score:
            best, best_score = c, s

    if best and best_score >= AUTO_THRESHOLD:
        tier = "fuzzy"
    elif best and best_score >= REVIEW_THRESHOLD:
        tier = "review"
    else:
        return MatchResult(provider_code, provider_name, parent_key, None, None, best_score, "new")
    return MatchResult(provider_code, provider_name, parent_key, best.pcode, best.name, best_score, tier)
