# Generated by Django 4.2.1 on 2023-05-24 13:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("timor_locations", "0002_remove_administrativepost_id_remove_municipality_id_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="administrativepost",
            name="municipality",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to="timor_locations.municipality"
            ),
        ),
        migrations.AlterField(
            model_name="administrativepost",
            name="pcode",
            field=models.IntegerField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="municipality",
            name="pcode",
            field=models.IntegerField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="suco",
            name="adminpost",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT, to="timor_locations.administrativepost"
            ),
        ),
        migrations.AlterField(
            model_name="suco",
            name="pcode",
            field=models.IntegerField(primary_key=True, serialize=False),
        ),
    ]
