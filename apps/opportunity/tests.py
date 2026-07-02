from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.opportunity.models import BusinessClimateProfile, BusinessClimateReview
from apps.opportunity.tasks import generate_business_climate_profile_task
from tests.factories import CountryFactory, RegionFactory

pytestmark = pytest.mark.django_db


def _make_profile(country, region=None, published=True):
    profile = BusinessClimateProfile.objects.create(
        country=country, region=region, overall_complexity_score=70,
    )
    if published:
        review = BusinessClimateReview.objects.create(
            profile=profile, generated_at=timezone.now(),
            confidence_score=80, status="approved",
        )
        profile.published_review = review
        profile.save(update_fields=["published_review"])
    return profile


class TestPublishGating:
    def test_unpublished_profile_is_not_visible_via_public_api(self, api_client):
        country = CountryFactory()
        _make_profile(country, published=False)
        resp = api_client.get(
            reverse("api_v1:country-business-climate", args=[country.iso2])
        )
        assert resp.status_code == 404

    def test_published_profile_is_visible_via_public_api(self, api_client):
        country = CountryFactory()
        _make_profile(country, published=True)
        resp = api_client.get(
            reverse("api_v1:country-business-climate", args=[country.iso2])
        )
        assert resp.status_code == 200
        assert resp.data["overall_complexity_score"] == 70

    def test_unknown_country_404s(self, api_client):
        resp = api_client.get(
            reverse("api_v1:country-business-climate", args=["ZZ"])
        )
        assert resp.status_code == 404

    def test_regenerating_does_not_unpublish_previous_version(self):
        country = CountryFactory()
        profile = _make_profile(country, published=True)
        original_review = profile.published_review

        # Regenerate: a fresh pending review is created but the old
        # approved one must remain the published one.
        BusinessClimateReview.objects.create(
            profile=profile, generated_at=timezone.now(),
            confidence_score=50, status="pending_review",
        )
        profile.refresh_from_db()
        assert profile.published_review_id == original_review.id


class TestRegionOverrideResolution:
    def test_region_specific_profile_overrides_country_default(self, api_client):
        region = RegionFactory(slug="canggu", name="Canggu")
        country_profile = _make_profile(region.country, region=None, published=True)
        country_profile.overall_complexity_score = 60
        country_profile.save()

        region_profile = _make_profile(region.country, region=region, published=True)
        region_profile.overall_complexity_score = 90
        region_profile.save()

        resp = api_client.get(
            reverse("api_v1:country-business-climate", args=[region.country.iso2]),
            {"region": str(region.id)},
        )
        assert resp.status_code == 200
        assert resp.data["overall_complexity_score"] == 90

    def test_falls_back_to_country_default_when_no_region_override_exists(self, api_client):
        region = RegionFactory(slug="ubud", name="Ubud")
        _make_profile(region.country, region=None, published=True)

        resp = api_client.get(
            reverse("api_v1:country-business-climate", args=[region.country.iso2]),
            {"region": str(region.id)},
        )
        assert resp.status_code == 200


class TestGenerateBusinessClimateProfileTask:
    def test_creates_profile_and_pending_review_never_auto_publishes(self):
        country = CountryFactory()
        fake_result = {
            "foreign_land_ownership_summary": "Leasehold only for foreigners.",
            "foreign_land_ownership_score": 40,
            "business_registration_summary": "PT PMA required.",
            "business_registration_days_estimate": 30,
            "business_registration_cost_usd_estimate": 1500.0,
            "business_registration_score": 55,
            "tax_overview_summary": "Corporate tax 22%.",
            "corporate_tax_rate_pct": 22.0,
            "personal_income_tax_top_rate_pct": 35.0,
            "investor_visa_summary": "Second Home Visa available.",
            "has_digital_nomad_visa": True,
            "has_investor_residency_program": True,
            "overall_complexity_score": 65,
            "confidence_score": 72,
            "sources": [{"label": "Heritage Index", "url": "https://example.com", "excerpt": "..."}],
        }
        with override_settings(GROQ_API_KEY="test-key"), patch(
            "apps.opportunity.llm.GroqClient.generate_business_climate",
            return_value=fake_result,
        ), patch("apps.opportunity.indexes.base.fetch_all_grounding", return_value=[]):
            result = generate_business_climate_profile_task(country.iso2)

        assert result["status"] == "pending_review"
        profile = BusinessClimateProfile.objects.get(country=country, region=None)
        assert profile.overall_complexity_score == 65
        assert profile.is_published is False
        assert profile.sources.count() == 1
        review = BusinessClimateReview.objects.get(profile=profile)
        assert review.status == "pending_review"
        assert review.confidence_score == 72
