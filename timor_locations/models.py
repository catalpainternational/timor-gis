import json

from django.contrib.gis.db.models import MultiPolygonField
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import MultiPolygon

from timor_locations.gis_functions import Quantize, SimplifyPreserve
from timor_locations.schemas import Topology


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

        return self.annotate(geojson=AsGeoJSON(g))

    def as_feature_list(self, **kwargs) -> list[Feature]:
        return [instance.as_feature() for instance in self.annotate_geo_json(**kwargs)]

    def as_feature_collection(self, **kwargs):
        return FeatureCollection.construct(type="FeatureCollection", features=self.as_feature_list())


class GeoDataManager(models.Manager):
    def get_queryset(self) -> GeoQuerySet:
        return GeoQuerySet(self.model, using=self._db)

    def as_feature_list(self, **kwargs) -> list[Feature]:
        return self.get_queryset().as_feature_list(**kwargs)

    def as_feature_collection(self, **kwargs):
        return self.get_queryset().as_feature_collection(**kwargs)


class TimorGeoArea(DateStampedModel):
    class Meta:
        abstract = True

    pcode = models.IntegerField(primary_key=True)
    geom = MultiPolygonField(srid=4326, blank=True, null=True)
    name = models.CharField(max_length=100)
    objects = GeoDataManager()

    def __str__(self):
        return self.name

    def as_multipolygon(self):
        """
        When used as part of the 'GeoDataManager' the `geojson` property represents a possibly
        quantized / simplified geometry. Otherwise, if this is a single instance, uses the GEOS library
        to fetch the GeoJSON.
        """
        if not hasattr(self, "geojson"):
            return MultiPolygon.construct(**json.loads(self.geom.json))
        return MultiPolygon.construct(**json.loads(self.geojson))

    def as_feature(self):
        properties = dict(name = self.name, id=self.pcode, kind=self._meta.model_name)

        for optional in ("adminpost_id", "municipality_id"):
            if hasattr(self, optional):
                properties[optional] = getattr(self, optional)
            
        return Feature.construct(
            type="Feature", id=self.pcode, properties=properties, geometry=self.as_multipolygon()
        )

    @classmethod
    def all_features(cls, **kwargs) -> FeatureCollection:
        """
        Returns a FeatureCollection with **ALL** features from Municipality, Admin Post, and Suco
        """
        return FeatureCollection.construct(
            type="FeatureCollection",
            features=[
                *Municipality.objects.as_feature_list(**kwargs),
                *AdministrativePost.objects.as_feature_list(**kwargs),
                *Suco.objects.as_feature_list(**kwargs),
            ],
        )

    @classmethod
    def topology(cls):
        import topojson
        return topojson.Topology(cls.all_features().json())


class Municipality(TimorGeoArea):
    pass


class AdministrativePost(TimorGeoArea):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, null=True)


class Suco(TimorGeoArea):
    adminpost = models.ForeignKey(AdministrativePost, on_delete=models.PROTECT, null=True)


class TopoJson(models.Model):
    """
    Stores topology instances developed from other geo information
    """

    id = models.SlugField(primary_key=True, max_length=2048)
    name = models.CharField(null=True, blank=True, max_length=2048)
    quantization = models.DecimalField(max_digits=16, decimal_places=8)
    simplification = models.DecimalField(max_digits=16, decimal_places=8)
    topojson = models.JSONField()

    @property
    def topology(self):
        """
        Apparently, topoJSON is order dependent for OGR :(
        """
        return Topology(
            type="Topology",
            objects=self.topojson["objects"],
            bbox=self.topojson["bbox"],
            transform=self.topojson["transform"],
            arcs=self.topojson["arcs"],
        )
