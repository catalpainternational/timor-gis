import os
from importlib import resources

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping
from django.core.management.base import BaseCommand
from django.db import connection

from timor_locations.models import AdministrativePost, Aldeia, Municipality, Suco
from timor_locations.suco_resolve import SucoIndex

aldeia_mapping = {"geom": "MULTIPOLYGON", "name": "ALDEIA", "pcode": "NewAldCode"}
SOURCE_GEO = resources.files("timor_locations.data").joinpath("aldeias_2024.gpkg")


class Command(BaseCommand):
    help = "Import Timor data from source shapefiles."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Priming the Districts table"))

        if not os.path.exists(SOURCE_GEO):
            raise FileNotFoundError(f"The geographic data is not present: expected a file at {SOURCE_GEO}")

        suco_index = SucoIndex.from_sukus_gpkg()
        ds = DataSource(SOURCE_GEO)
        sucos_preloaded = Suco._base_manager.exists()

        lm = LayerMapping(Aldeia, ds, aldeia_mapping)
        self.stdout.write(self.style.SUCCESS("Saving aldeias from the gpkg file"))
        lm.save()

        self.stdout.write(
            self.style.SUCCESS(
                "Linking aldeias to sucos via sukus.gpkg (spatial); "
                "aldeia NewSucoCod is not trusted when it disagrees with Suco.shp"
            )
        )

        layer = ds[0]
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

        ids: set[str] = set()
        remapped = 0

        for NewAldCode, NewSucoCod, NewPostAdC, NewMunCode, ALDEIA, SUCO, P_ADMIN, MUNICIPIO in names:
            aldeia = Aldeia._base_manager.get(pcode=NewAldCode)
            resolved_suco = suco_index.resolve_pcode(aldeia.geom, NewSucoCod, SUCO)
            if resolved_suco != NewSucoCod:
                remapped += 1

            if not sucos_preloaded:
                # _base_manager (plain Manager): the default GeoDataManager annotates nullable
                # FK joins, and update_or_create's locking SELECT then trips "FOR UPDATE cannot be
                # applied to the nullable side of an outer join" on Django 4.2+.
                # Match hierarchy rows on pcode (the PK) only so this importer composes with
                # import_timor_geo_data, which may have already loaded sucos from sukus.gpkg.
                if NewMunCode not in ids:
                    municipality, _ = Municipality._base_manager.update_or_create(
                        pcode=NewMunCode, defaults=dict(name=MUNICIPIO)
                    )
                    ids.add(NewMunCode)
                    self.stdout.write(self.style.SUCCESS(f"ADDED {municipality}"))

                if NewPostAdC not in ids:
                    adminpost, _ = AdministrativePost._base_manager.update_or_create(
                        pcode=NewPostAdC, defaults=dict(name=P_ADMIN, municipality_id=NewMunCode)
                    )
                    ids.add(NewPostAdC)
                    self.stdout.write(self.style.SUCCESS(f"ADDED {adminpost}"))

                if resolved_suco not in ids:
                    suco_name = suco_index.suco_name(resolved_suco)
                    suco, _ = Suco._base_manager.update_or_create(
                        pcode=resolved_suco, defaults=dict(name=suco_name, adminpost_id=NewPostAdC)
                    )
                    ids.add(resolved_suco)
                    self.stdout.write(self.style.SUCCESS(f"ADDED {suco}"))

            aldeia.suco_id = resolved_suco
            aldeia.save(update_fields=["suco_id"])
            ids.add(NewAldCode)
            self.stdout.write(self.style.SUCCESS(f"LINKED {aldeia} -> suco {resolved_suco}"))

        self.stdout.write(self.style.SUCCESS(f"Remapped {remapped} aldeias off stale aldeia-layer NewSucoCod values"))

        if sucos_preloaded:
            self.stdout.write(
                self.style.SUCCESS(
                    "Skipping suco/adminpost/municipality geometry rollup — "
                    "sucos were already loaded from sukus.gpkg via import_timor_geo_data"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Populate the suco / admin post / municipality geometries based on the Aldeia geometries"
                )
            )
            with connection.cursor() as c:
                c.execute(
                    """
                    UPDATE timor_locations_suco sc
                        SET geom = (
                            SELECT st_multi(st_union(geom)) FROM timor_locations_aldeia a
                            WHERE a.suco_id = sc.pcode
                        );
                    UPDATE timor_locations_administrativepost ap
                        SET geom = (
                            SELECT st_multi(st_union(geom)) FROM timor_locations_suco s
                            WHERE s.adminpost_id = ap.pcode
                        );
                    UPDATE timor_locations_municipality m
                        SET geom = (
                            SELECT st_multi(st_union(geom)) FROM timor_locations_administrativepost ap
                            WHERE ap.municipality_id = m.pcode
                        );
                    """
                )
