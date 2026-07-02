from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Continent, Country, Region


class ContinentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Continent
        fields = ["id", "code", "name", "slug"]


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = [
            "id", "name", "slug", "level", "parent",
            "centroid_lat", "centroid_lng",
        ]


class CountrySerializer(GeoFeatureModelSerializer):
    continent = ContinentSerializer(read_only=True)
    regions = RegionSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        geo_field = "boundary"
        fields = [
            "iso2", "iso3", "name", "continent", "centroid_lat", "centroid_lng",
            "currency_code", "flag_emoji", "is_housing_supported", "regions",
        ]
