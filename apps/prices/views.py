from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend

from apps.geo.models import Country, Region
from .models import PriceRecord, DailyAggregate
from .serializers import PriceRecordSerializer, DailyAggregateSerializer, PriceTrendSerializer
from .services import PriceAnalysisService


class PriceRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PriceRecord.objects.select_related("source", "country", "region").all()
    serializer_class = PriceRecordSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["country", "region", "market_type", "property_type", "source"]
    ordering_fields = ["scraped_at", "price_usd"]

    @action(detail=False, methods=["get"], url_path="trend")
    def trend(self, request):
        """Returns price trend for a given country[/region]/market_type over N days."""
        country_iso2 = request.query_params.get("country")
        if not country_iso2:
            raise ValidationError({"country": "This query parameter is required."})
        try:
            country = Country.objects.get(iso2=country_iso2.upper())
        except Country.DoesNotExist:
            raise ValidationError({"country": "Unknown country code."})

        region = None
        region_id = request.query_params.get("region")
        if region_id:
            try:
                region = Region.objects.get(pk=region_id, country=country)
            except (Region.DoesNotExist, ValueError):
                raise ValidationError({"region": "Unknown region for this country."})

        market_type = request.query_params.get("market_type", "rental")
        raw_days = request.query_params.get("days", "30")
        try:
            days = int(raw_days)
        except (ValueError, TypeError):
            raise ValidationError({"days": "Must be an integer."})
        if not (1 <= days <= 365):
            raise ValidationError({"days": "Must be between 1 and 365."})
        data = PriceAnalysisService.get_trend(
            country=country, region=region, market_type=market_type, days=days
        )
        serializer = PriceTrendSerializer(data, many=True)
        return Response(serializer.data)


class DailyAggregateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DailyAggregate.objects.all()
    serializer_class = DailyAggregateSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["country", "region", "market_type", "property_type", "date"]
    ordering_fields = ["date", "avg_price_usd"]
