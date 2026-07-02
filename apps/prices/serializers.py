from rest_framework import serializers
from .models import PriceRecord, DailyAggregate


class PriceRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)

    class Meta:
        model = PriceRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class DailyAggregateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyAggregate
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class PriceTrendSerializer(serializers.Serializer):
    """Used for trend analysis endpoint response."""
    date = serializers.DateField()
    avg_price_usd = serializers.DecimalField(max_digits=12, decimal_places=2)
    price_change_pct = serializers.DecimalField(max_digits=6, decimal_places=2, allow_null=True)
    listings_count = serializers.IntegerField()
