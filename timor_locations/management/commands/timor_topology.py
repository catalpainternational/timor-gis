from django.core.management.base import BaseCommand
from django.db import connection

from timor_locations import models


class Command(BaseCommand):
    help = "Commands necessary to build timor 'topology' layer in postgis"

    def handle(self, *args, **options):
        topology_schema_name = "topo"

        precision = 1e-6
        tolerance = 0
        srid = 4326

        # Which table name and column name to use for the "topo" references
        schema_name = "public"
        table_name = models.TimorTopology._meta.db_table
        column_name = "topo"
        geomtype = "POLYGON"

        self.stdout.write(self.style.SUCCESS("Creating topology"))
        with connection.cursor() as c:
            c.execute(f"SELECT topology.DropTopology('{topology_schema_name}')")
            c.execute(f"SELECT topology.CreateTopology('{topology_schema_name}', {srid}, {precision});")
            # Add topology from the 'suco' table
            c.execute(f"DROP TABLE IF EXISTS {schema_name}.{table_name}")
            c.execute(f"CREATE TABLE {schema_name}.{table_name} (pcode int PRIMARY KEY)")
            c.execute(
                f"SELECT topology.AddTopoGeometryColumn('{topology_schema_name}', '{schema_name}', '{table_name}', '{column_name}', '{geomtype}');"
            )

            for model in models.Municipality, models.AdministrativePost, models.Suco:
                self.stdout.write(self.style.SUCCESS(f"import {model.objects.count()} geoms from {model}"))

                c.execute(
                    f"""
                    INSERT INTO {schema_name}.{table_name} (pcode, {column_name})
                    SELECT  pcode, topology.toTopoGeom(geom, '{topology_schema_name}', 1, {tolerance})
                    FROM {model._meta.db_table}
                    """
                )
