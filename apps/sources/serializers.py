from rest_framework import serializers
from .models import Source, ScrapeJob


class SourceSerializer(serializers.ModelSerializer):
    country_iso2 = serializers.CharField(source="country.iso2", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    region_name = serializers.SerializerMethodField()

    class Meta:
        model = Source
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def get_region_name(self, obj) -> str | None:
        return obj.region.name if obj.region else None


class ScrapeJobSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = ScrapeJob
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
