"""Seed ProviderCode rows from the committed suco crosswalk.

The crosswalk links the Estrada integer code (``canonical_pcode``) to the INTL
code (``provider_code``) per suco. We emit one ProviderCode for each scheme, both
pointing at the Suco (whose PK is the INTL code). Run AFTER import_timor_geo_data.

Suco-level only: the crosswalk does not carry a legacy<->INTL bridge for admin
posts, municipalities or aldeias, so those are left unseeded (see README).
"""

import csv
from pathlib import Path

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from timor_locations.models import ProviderCode, Suco

XWALK = Path(__file__).resolve().parents[2] / "data" / "crosswalk" / "suco_crosswalk.csv"


class Command(BaseCommand):
    help = "Seed ProviderCode rows from the committed suco crosswalk."

    def add_arguments(self, parser):
        parser.add_argument("--crosswalk", default=str(XWALK))

    @transaction.atomic
    def handle(self, *args, **opts):
        path = Path(opts["crosswalk"])
        if not path.exists():
            raise CommandError(f"crosswalk not found: {path}")

        ct = ContentType.objects.get_for_model(Suco)
        ProviderCode.objects.filter(content_type=ct).delete()  # idempotent reseed

        made, skipped = 0, 0
        for r in csv.DictReader(path.open()):
            intl = r["provider_code"].strip()
            status = (r["status"] or "matched").strip()
            if not Suco._base_manager.filter(pcode=intl).exists():
                self.stderr.write(f"skip {intl}: no Suco (run import_timor_geo_data first)")
                skipped += 1
                continue
            score = float(r["score"]) if r.get("score") else None

            # current canonical coding (INTL)
            ProviderCode.objects.create(
                scheme="intl2024",
                code=intl,
                name=r["provider_name"].strip(),
                relation="new" if status == "new" else "matched",
                content_type=ct,
                object_id=intl,
            )
            made += 1

            # prior coding (Estrada), when this suco had one
            estrada = (r.get("canonical_pcode") or "").strip()
            if status != "new" and estrada:
                ProviderCode.objects.create(
                    scheme="estrada",
                    code=estrada,
                    name=(r.get("canonical_name") or "").strip(),
                    relation="rename" if status == "rename" else "matched",
                    score=score,
                    note=(r.get("note") or "").strip(),
                    content_type=ct,
                    object_id=intl,
                )
                made += 1

        self.stdout.write(self.style.SUCCESS(f"Loaded {made} ProviderCode rows ({skipped} sucos skipped)"))
