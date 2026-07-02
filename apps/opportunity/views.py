from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAdminUser

from apps.geo.models import Country

from .models import BusinessClimateProfile, BusinessClimateReview
from .serializers import BusinessClimateProfileSerializer, BusinessClimateReviewSerializer


class CountryBusinessClimateView(RetrieveAPIView):
    """GET /api/v1/opportunity/countries/{iso2}/[?region=<uuid>]

    Resolves a region-level override profile first, falling back to the
    country-level default. Only ever returns a *published* profile (has an
    approved review) — never leaks unreviewed LLM output.
    """

    serializer_class = BusinessClimateProfileSerializer
    permission_classes = [AllowAny]
    lookup_url_kwarg = "iso2"

    def get_object(self):
        iso2 = self.kwargs["iso2"].upper()
        country = Country.objects.filter(iso2=iso2).first()
        if country is None:
            raise NotFound("Unknown country.")

        region_id = self.request.query_params.get("region")
        qs = BusinessClimateProfile.objects.filter(
            country=country, published_review__isnull=False
        ).select_related("country", "region", "published_review")

        profile = None
        if region_id:
            profile = qs.filter(region_id=region_id).first()
        if profile is None:
            profile = qs.filter(region__isnull=True).first()
        if profile is None:
            raise NotFound("No published business-climate profile for this country yet.")
        return profile


class BusinessClimateReviewViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin-only — lets a reviewer see pending profiles before approving
    them in the Django admin (approval itself happens there, not via API)."""

    queryset = BusinessClimateReview.objects.select_related("profile", "reviewed_by").all()
    serializer_class = BusinessClimateReviewSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["status"]
