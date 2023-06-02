# Generated by Django 4.2.1 on 2023-06-02 01:12

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timor_locations', '0006_timortopology_edgemap'),
    ]

    operations = [
        migrations.CreateModel(
            name='Aldeia',
            fields=[
                ('date_created', models.DateField(auto_now_add=True, null=True, verbose_name='Date Created')),
                ('date_modified', models.DateField(auto_now=True, null=True, verbose_name='Last Modified')),
                ('pcode', models.IntegerField(primary_key=True, serialize=False)),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(blank=True, null=True, srid=4326)),
                ('name', models.CharField(max_length=100)),
                ('suco', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='timor_locations.suco')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.DeleteModel(
            name='Edgemap',
        ),
        migrations.DeleteModel(
            name='TimorTopology',
        ),
    ]
