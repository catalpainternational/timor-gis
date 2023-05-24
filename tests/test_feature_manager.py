from django.db.models import QuerySet
from django.test import TestCase

from timor_locations.models import Municipality
from geojson_pydantic import Feature
from tests.factories import AreaFactory  # type: ignore


class FeatureManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.area = AreaFactory()

    def test_features(self):
        """
        Test the 'JSONObject' based manager which returns features
        """
        queryset: QuerySet[Municipality] = Municipality.objects.all()

        # Assert that the "feature" is correctly a field on the queryset
        collection = queryset[:1].as_feature_collection()
        self.assertIsInstance(collection.features[0], Feature)