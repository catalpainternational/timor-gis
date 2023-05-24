import factory
import factory.fuzzy
from django.contrib.gis.geos import MultiPolygon, Polygon
from factory.django import DjangoModelFactory

from timor_locations.models import Municipality


class AreaFactory(DjangoModelFactory):
    class Meta:
        model = Municipality
        django_get_or_create = ("pcode",)

    pcode = factory.fuzzy.FuzzyInteger(low=100, high=10000)
    name = factory.fuzzy.FuzzyText()
    geom = MultiPolygon(Polygon(((0, 0), (0, 1), (1, 1), (0, 0))), Polygon(((1, 1), (1, 2), (2, 2), (1, 1))))
