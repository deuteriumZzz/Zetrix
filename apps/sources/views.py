from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend

from .models import Source, ScrapeJob
from .serializers import SourceSerializer, ScrapeJobSerializer
from .tasks import scrape_source_task
from apps.core.mixins import TriggerActionMixin


class SourceViewSet(TriggerActionMixin, viewsets.ModelViewSet):
    queryset = Source.objects.select_related("country", "region").all()
    serializer_class = SourceSerializer
    trigger_task = scrape_source_task
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["source_type", "market_type", "country", "region", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["created_at", "country", "source_type"]

    @action(detail=False, methods=["get"], url_path="by-region")
    def by_region(self, request):
        """Returns active sources, optionally filtered by country (iso2) and/or region (UUID)."""
        country_iso2 = request.query_params.get("country")
        region_id = request.query_params.get("region")
        qs = self.get_queryset().filter(is_active=True)
        if country_iso2:
            qs = qs.filter(country__iso2=country_iso2.upper())
        if region_id:
            qs = qs.filter(region_id=region_id)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ScrapeJobViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScrapeJob.objects.select_related("source").all()
    serializer_class = ScrapeJobSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["source", "status"]
    ordering_fields = ["created_at", "started_at", "finished_at"]
