import csv
import os
from importlib import resources

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping
from django.core.management.base import BaseCommand
from django.db import connection

from timor_locations.models import AdministrativePost, Aldeia, Municipality, Suco

aldeia_mapping = {"geom": "MULTIPOLYGON", "name": "ALDEIA", "pcode": "NewAldCode"}
SOURCE_GEO = resources.files("timor_locations.data").joinpath("aldeias_2022.gpkg")


class Command(BaseCommand):
    help = "Import Timor data from source shapefiles."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Priming the Districts table"))

        if not os.path.exists(SOURCE_GEO):
            raise FileNotFoundError(f"The geographic data is not present: expected a file at {SOURCE_GEO}")

        ds = DataSource(SOURCE_GEO)

        # if Aldeia.objects.count() or Suco.objects.count() or AdministrativePost.objects.count() or Municipality.objects.count():
        #     raise NotImplementedError("Please clear the tables before import")

        lm = LayerMapping(Aldeia, ds, aldeia_mapping)
        self.stdout.write(self.style.SUCCESS("Saving aldeias from the gpkg file"))
        # lm.save()

        self.stdout.write(self.style.SUCCESS("Adding admin posts and municipalities"))

        layer = ds[0]
        # Fetch the ID & name of aldeia suco, pa, mun
        names = zip(
            *(
                layer.get_fields(f)
                for f in (
                    "NewAldCode",
                    "NewSucoCod",
                    "NewPostAdC",
                    "NewMunCode",
                    "ALDEIA",
                    "SUCO",
                    "P_ADMIN",
                    "MUNICIPIO",
                )
            )
        )

        ids: set[int] = set()

        for NewAldCode, NewSucoCod, NewPostAdC, NewMunCode, ALDEIA, SUCO, P_ADMIN, MUNICIPIO in names:
            print(NewAldCode, NewSucoCod, NewPostAdC, NewMunCode, ALDEIA, SUCO, P_ADMIN, MUNICIPIO)

            if NewMunCode not in ids:
                municipality, _ = Municipality.objects.get_or_create(pcode=NewMunCode, name=MUNICIPIO)
                ids.add(NewMunCode)
                self.stdout.write(self.style.SUCCESS(f"ADDED {municipality}"))

            if NewPostAdC not in ids:
                adminpost, _ = AdministrativePost.objects.get_or_create(
                    pcode=NewPostAdC, name=P_ADMIN, municipality_id=NewMunCode
                )
                ids.add(NewPostAdC)
                self.stdout.write(self.style.SUCCESS(f"ADDED {adminpost}"))

            if NewSucoCod not in ids:
                suco, _ = Suco.objects.get_or_create(pcode=NewSucoCod, name=SUCO, adminpost_id=NewPostAdC)
                ids.add(NewSucoCod)
                self.stdout.write(self.style.SUCCESS(f"ADDED {suco}"))

            aldeia = Aldeia.objects.get(pcode=NewAldCode)
            aldeia.suco_id = NewSucoCod
            aldeia.save()
            ids.add(NewAldCode)
            self.stdout.write(self.style.SUCCESS(f"ADDED {aldeia}"))

        self.stdout.write(
            self.style.SUCCESS(
                "Populate the suco / admin post / municipality geometries based on the Aldeia geometries"
            )
        )
        with connection.cursor() as c:
            c.execute(
                """
                UPDATE timor_locations_suco sc
                    SET geom = (SELECT st_multi(st_union(geom)) FROM timor_locations_aldeia a WHERE a.suco_id = sc.pcode);
                UPDATE timor_locations_administrativepost ap
                    SET geom = (SELECT st_multi(st_union(geom)) FROM timor_locations_suco s WHERE s.adminpost_id = ap.pcode);
                UPDATE timor_locations_municipality m
                    SET geom = (SELECT st_multi(st_union(geom)) FROM timor_locations_administrativepost ap WHERE ap.municipality_id = m.pcode);
                """
            )
