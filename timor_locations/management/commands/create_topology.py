try:
    import topojson
except ModuleNotFoundError as E:
    raise ModuleNotFoundError(
        "You may need to install the optional `topology` group: `poetry install --only topology`"
    ) from E

from django.core.management.base import BaseCommand

from timor_locations.models import TimorGeoArea, TopoJson


class Command(BaseCommand):
    help = "Create or update topology entries in the database"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("(1) Fetching features"))
        features = TimorGeoArea.all_features()
        self.stdout.write(self.style.SUCCESS("(2) JSON features"))
        json_output = features.json()
        self.stdout.write(self.style.SUCCESS("(3) Topology (This may take some time)"))
        topology = topojson.Topology(json_output)

        # Add different outputs for "quantize" and "simplify"
        simplify = [0, 5e-5, 1e-4, 1e-3]
        quantize_values = [0, 5e5, 1e5, 1e4]
        slugs = ["original-detail", "high-detail", "mid-detail", "low-detail"]

        for s, q, slug in zip(simplify, quantize_values, slugs):
            TopoJson.objects.update_or_create(
                id=slug,
                defaults=dict(
                    name=slug,
                    quantization=q,
                    simplification=s,
                    topojson=topology.topoquantize(q).toposimplify(s).to_dict() if q and s else topology.to_dict(),
                ),
            )
