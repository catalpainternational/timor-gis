# Generated by Django 4.2.1 on 2023-05-24 07:32

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AdministrativePost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date_created", models.DateField(auto_now_add=True, null=True, verbose_name="Date Created")),
                ("date_modified", models.DateField(blank=True, null=True, verbose_name="Last Modified")),
                ("geom", django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
                ("pcode", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Municipality",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date_created", models.DateField(auto_now_add=True, null=True, verbose_name="Date Created")),
                ("date_modified", models.DateField(blank=True, null=True, verbose_name="Last Modified")),
                ("geom", django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
                ("pcode", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=100)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Suco",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date_created", models.DateField(auto_now_add=True, null=True, verbose_name="Date Created")),
                ("date_modified", models.DateField(blank=True, null=True, verbose_name="Last Modified")),
                ("geom", django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
                ("pcode", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=100)),
                (
                    "adminpost",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to="timor_locations.administrativepost"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="administrativepost",
            name="municipality",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="timor_locations.municipality"),
        ),
    ]
