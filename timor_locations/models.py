
from django.contrib.gis.db.models import MultiPolygonField
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import MultiPolygon
from django.contrib.gis.db.models.functions import AsGeoJSON
import json

from timor_locations.gis_functions import Quantize, SimplifyPreserve

class DateStampedModel(models.Model):
    date_created = models.DateField(verbose_name=_("Date Created"), auto_now_add=True, null=True, blank=True)
    date_modified = models.DateField(verbose_name=_("Last Modified"), auto_now=True, null=True, blank=True)

    class Meta:
        abstract = True


class GeoQuerySet(models.QuerySet):

    def annotate_geo_json(self, simplify: float | None = None, quantize: int | None = None):
        
        g = F("geom")

        if simplify:
            g = SimplifyPreserve(g, simplify=simplify)
        if quantize:
            g = Quantize(g, quantize=quantize)

        return self.annotate(geojson = AsGeoJSON(g))

    def as_feature_collection(self, simplify: float | None = None, quantize: int | None = None):
        return FeatureCollection.construct(
            type="FeatureCollection",
            features = [
                Feature.construct(
                    type="Feature",
                    id = instance.pcode,
                    properties = {"name": instance.name},
                    geometry = MultiPolygon.construct(**json.loads(instance.geojson))
                ) for instance in self.annotate_geo_json(simplify, quantize)
            ]
        )

class GeoDataManager(models.Manager):

    def get_queryset(self) -> GeoQuerySet:
        return GeoQuerySet(self.model, using=self._db)

    def as_feature_collection(self, simplify: float | None = None, quantize: int | None = None):
        return self.get_queryset().as_feature_collection(simplify, quantize)


class TimorGeoArea(DateStampedModel):
    class Meta:
        abstract = True

    pcode = models.IntegerField(primary_key=True)
    geom = MultiPolygonField(srid=4326, blank=True, null=True)
    name = models.CharField(max_length=100)
    objects = GeoDataManager()

    def __str__(self):
        return self.name


class Municipality(TimorGeoArea):
    pass

class AdministrativePost(TimorGeoArea):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, null=True)

class Suco(TimorGeoArea):
    adminpost = models.ForeignKey(AdministrativePost, on_delete=models.PROTECT, null=True)
