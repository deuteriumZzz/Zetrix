from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from .models import Continent, Country, Region
from .serializers import ContinentSerializer, CountrySerializer, RegionSerializer


class ContinentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Continent.objects.all()
    serializer_class = ContinentSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Country.objects.select_related("continent").prefetch_related("regions").all()
    serializer_class = CountrySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    lookup_field = "iso2"
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["continent", "is_housing_supported"]


class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Region.objects.select_related("country", "parent").all()
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["country", "parent", "level"]
