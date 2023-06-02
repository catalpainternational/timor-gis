# Generated by Django 3.2.12 on 2022-03-24 10:38

from typing import List, Tuple

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies: List[Tuple[str, str]] = []

    operations = [
        migrations.CreateModel(
            name="MercatorPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", django.contrib.gis.db.models.fields.PointField(srid=3857)),
            ],
        ),
        migrations.CreateModel(
            name="WgsPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ],
        ),
    ]
