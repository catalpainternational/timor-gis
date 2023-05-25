from importlib import resources
import os
from django.core.management.base import BaseCommand
from pathlib import Path
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping
from django.db import connection
from timor_locations.models import Suco, AdministrativePost, Municipality
import csv


suco_mapping = {"geom": "MULTIPOLYGON", "name": "SUCONAME", "pcode": "SUCOCODE"}

# Data for this is help in Git LFS


SOURCE_GEO = resources.files('timor_locations.data').joinpath('sukus.gpkg')
SOURCE_CSV = resources.files('timor_locations.data').joinpath('sukus.csv')

class Command(BaseCommand):
    help = "Import Timor data from source shapefiles."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Priming the Districts table"))

        if not os.path.exists(SOURCE_GEO):
            raise FileNotFoundError(f"The geographic data is not present: expected a file at {SOURCE_GEO}")
        if not os.path.exists(SOURCE_CSV):
            raise FileNotFoundError(f"The CSV file for data is not present: expected a file at {SOURCE_CSV}")

        ds = DataSource(SOURCE_GEO)

        lm = LayerMapping(Suco, ds, suco_mapping)
        self.stdout.write(self.style.SUCCESS("Saving sucos from the gpkg file"))
        lm.save()

        self.stdout.write(self.style.SUCCESS("Adding admin posts and municipalities"))

        with open(SOURCE_CSV) as csvfile:
            csvreader = csv.reader(csvfile)
            posts: list[str, str] = list(csvreader)[1:]
            for SUCONAME, SUBDSTCODE, DISTCODE, DISTNAME, SUBDISTRCT, SUCOCODE, REGION in posts:
                municipality, _ = Municipality.objects.update_or_create(pcode=DISTCODE, defaults=dict(name=DISTNAME))
                adminpost, _ = AdministrativePost.objects.update_or_create(
                    pcode=SUBDSTCODE, defaults=dict(name=SUBDISTRCT, municipality=municipality)
                )
                suco, _ = Suco.objects.update_or_create(
                    pcode=SUCOCODE, defaults=dict(name=SUCONAME, adminpost=adminpost)
                )

        self.stdout.write(
            self.style.SUCCESS("Populate the admin post / municipality geometries based on the Suco geometries")
        )
        with connection.cursor() as c:
            c.execute(
                """
                UPDATE timor_locations_administrativepost ap 
                    SET geom = (SELECT st_multi(st_union(geom)) FROM timor_locations_suco s WHERE s.adminpost_id = ap.pcode);
                UPDATE timor_locations_municipality m
                    SET geom = (SELECT st_multi(st_union(geom)) FROM timor_locations_administrativepost ap WHERE ap.municipality_id = m.pcode);
                """
            )
