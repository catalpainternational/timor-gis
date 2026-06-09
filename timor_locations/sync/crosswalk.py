"""Load/save the versioned crosswalk that links provider features to canonical
entities.

The crosswalk is the durable memory of the sync pipeline. Each row is one
provider feature and the canonical entity it resolves to, with enough denormalised
admin context to regenerate the importer's gpkg/csv without re-reading anything
else. It is committed to git (small, text, reviewable in PRs) -- *not* to LFS.

Resolving a fresh provider drop reuses prior rows verbatim, so only genuinely new
or changed features need human attention next time.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from pathlib import Path

FIELDNAMES = [
    "provider",
    "provider_code",
    "provider_name",
    "provider_post",
    "provider_mun",
    "canonical_pcode",
    "canonical_name",
    "subdstcode",
    "distcode",
    "distname",
    "subdistrct",
    "region",
    "status",  # matched | new | review | removed
    "score",
    "note",
]


@dataclass
class CrosswalkRow:
    provider: str
    provider_code: str
    provider_name: str
    provider_post: str
    provider_mun: str
    canonical_pcode: str
    canonical_name: str
    subdstcode: str
    distcode: str
    distname: str
    subdistrct: str
    region: str
    status: str
    score: str = ""
    note: str = ""

    def as_csv(self) -> dict:
        return {k: ("" if v is None else str(v)) for k, v in asdict(self).items()}


def load(path: str | Path) -> list[CrosswalkRow]:
    path = Path(path)
    if not path.exists():
        return []
    keep = {f.name for f in fields(CrosswalkRow)}
    with path.open() as fh:
        return [CrosswalkRow(**{k: v for k, v in row.items() if k in keep}) for row in csv.DictReader(fh)]


def index_by_provider_code(rows: list[CrosswalkRow]) -> dict[tuple[str, str], CrosswalkRow]:
    return {(r.provider, r.provider_code): r for r in rows}


def save(path: str | Path, rows: list[CrosswalkRow]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows, key=lambda r: (r.provider, r.distcode.zfill(2), str(r.canonical_pcode).zfill(8)))
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in ordered:
            writer.writerow(r.as_csv())
