import json

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db.models import MultiPolygonField
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.db import models
from django.db.models import F, Q
from django.db.models.expressions import Combinable
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
        g: Combinable = F("geom")

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
        queryset = GeoQuerySet(self.model, using=self._db)
        if self.model == Suco:
            queryset = queryset.annotate(
                adminpost_name=F("adminpost__name"),
                municipality_name=F("adminpost__municipality__name"),
                municipality_id=F("adminpost__municipality__pcode"),
            )
        if self.model == AdministrativePost:
            queryset = queryset.annotate(municipality_name=F("municipality__name"))
        return queryset

    def as_feature_list(self, **kwargs) -> list[Feature]:
        return self.get_queryset().as_feature_list(**kwargs)

    def as_feature_collection(self, **kwargs):
        return self.get_queryset().as_feature_collection(**kwargs)


class TimorGeoArea(DateStampedModel):
    class Meta:
        abstract = True

    # pcode is the INTL "New*Cod" code (zero-padded string, e.g. suco "010106",
    # aldeia "08050104"). A CharField so leading zeros survive; it stays the PK.
    pcode = models.CharField(max_length=12, primary_key=True)
    geom = MultiPolygonField(srid=4326, blank=True, null=True)
    name = models.CharField(max_length=100)
    objects = GeoDataManager()
    # Codes this area carries in other schemes (Estrada, future vintages). The
    # crosswalk lives in ProviderCode, not a column-per-scheme. See code_for().
    codes = GenericRelation("ProviderCode")

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
        properties = dict(name=self.name, id=self.pcode, kind=self._meta.model_name)

        for optional in ("adminpost_id", "municipality_id", "adminpost_name", "municipality_name"):
            if hasattr(self, optional):
                properties[optional] = getattr(self, optional)

        return Feature.construct(type="Feature", id=self.pcode, properties=properties, geometry=self.as_multipolygon())

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
        import topojson  # type: ignore[import]

        return topojson.Topology(cls.all_features().json())


class Municipality(TimorGeoArea):
    pass


class AdministrativePost(TimorGeoArea):
    municipality = models.ForeignKey(Municipality, on_delete=models.PROTECT, null=True)


class Suco(TimorGeoArea):
    adminpost = models.ForeignKey(AdministrativePost, on_delete=models.PROTECT, null=True)


class Aldeia(TimorGeoArea):
    suco = models.ForeignKey(Suco, on_delete=models.PROTECT, null=True)


class CodeScheme(models.TextChoices):
    ESTRADA = "estrada", "Estrada (legacy integer codes)"
    INTL2024 = "intl2024", "INTL / PNDS 2024 (New*Cod)"
    # future schemes are added here -- or drop TextChoices and let `scheme` be free text


class CodeRelation(models.TextChoices):
    MATCHED = "matched", "Same entity, re-coded"
    RENAME = "rename", "Same entity, renamed"
    NEW = "new", "Introduced by this scheme; no prior code"
    REMOVED = "removed", "In a prior scheme; gone here"
    SPLIT = "split", "One prior entity became several"
    MERGE = "merge", "Several prior entities became one"


class ProviderCode(models.Model):
    """One (scheme, code) label for one canonical area.

    Every scheme an area has ever been coded in -- Estrada, INTL 2024, a future
    vintage -- is one row here. Adding a scheme is INSERTs, never a schema
    migration; splits/merges/new/removed are representable because each is a row
    with a `relation`, not a scalar column. The canonical area is whatever the
    app keys on today (the INTL pcode, via the GenericForeignKey).
    """

    scheme = models.CharField(max_length=32, choices=CodeScheme.choices)
    code = models.CharField(max_length=16)  # string -- leading zeros survive
    name = models.CharField(max_length=100, blank=True)  # name in this scheme (renames)
    relation = models.CharField(max_length=12, choices=CodeRelation.choices, default=CodeRelation.MATCHED)
    score = models.FloatField(null=True, blank=True)  # match confidence, if fuzzy
    note = models.CharField(max_length=200, blank=True)

    # which area this labels (Municipality/AdministrativePost/Suco/Aldeia)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=12)  # the area's pcode (PK is a CharField)
    area = GenericForeignKey("content_type", "object_id")

    class Meta:
        constraints = [
            # unique only for 1:1 relations; split/merge legitimately repeat a (scheme, code)
            models.UniqueConstraint(
                fields=["scheme", "code"],
                condition=Q(relation__in=["matched", "rename", "new"]),
                name="uniq_scheme_code_1to1",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"], name="timor_loc_content_obj_idx"),
            models.Index(fields=["scheme", "code"], name="timor_loc_scheme_code_idx"),
        ]

    def __str__(self):
        return f"{self.scheme}:{self.code} -> {self.area}"


def code_for(area, scheme):
    """The area's code in `scheme`, or None. Call this instead of `area.pcode`
    so the canonical scheme can change later without a downstream rewrite."""
    pc = area.codes.filter(scheme=scheme).first()
    return pc.code if pc else None


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
