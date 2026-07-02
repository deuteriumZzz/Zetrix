from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def generate_business_climate_profile_task(self, country_iso2: str, region_id: str | None = None) -> dict:
    """Generates (or regenerates) a BusinessClimateProfile for a country
    (optionally scoped to a region override) via DeepSeek, grounded by
    whatever index clients are registered. Always lands in PENDING_REVIEW —
    never auto-publishes. Refresh cadence: quarterly via Celery Beat,
    distinct from the daily scrape/aggregate cadence (this data changes
    slowly)."""
    from apps.geo.models import Country, Region
    from apps.opportunity.indexes.base import fetch_all_grounding
    from apps.opportunity.llm import GroqClient
    from apps.opportunity.models import (
        BusinessClimateProfile,
        BusinessClimateReview,
        ClimateDataSource,
    )

    try:
        country = Country.objects.get(iso2=country_iso2.upper())
        region = Region.objects.get(pk=region_id) if region_id else None

        grounding = fetch_all_grounding(country.iso3)
        result = GroqClient().generate_business_climate(country.name, grounding)

        profile, _ = BusinessClimateProfile.objects.update_or_create(
            country=country,
            region=region,
            defaults={
                "foreign_land_ownership_summary": result.get("foreign_land_ownership_summary", ""),
                "foreign_land_ownership_score": result.get("foreign_land_ownership_score"),
                "business_registration_summary": result.get("business_registration_summary", ""),
                "business_registration_days_estimate": result.get("business_registration_days_estimate"),
                "business_registration_cost_usd_estimate": result.get(
                    "business_registration_cost_usd_estimate"
                ),
                "business_registration_score": result.get("business_registration_score"),
                "tax_overview_summary": result.get("tax_overview_summary", ""),
                "corporate_tax_rate_pct": result.get("corporate_tax_rate_pct"),
                "personal_income_tax_top_rate_pct": result.get("personal_income_tax_top_rate_pct"),
                "investor_visa_summary": result.get("investor_visa_summary", ""),
                "has_digital_nomad_visa": bool(result.get("has_digital_nomad_visa")),
                "has_investor_residency_program": bool(result.get("has_investor_residency_program")),
                "overall_complexity_score": result.get("overall_complexity_score"),
            },
        )

        now = timezone.now()
        for src in result.get("sources", []):
            ClimateDataSource.objects.create(
                profile=profile,
                source_type="llm_generated",
                citation_url=src.get("url") or "",
                raw_excerpt=(src.get("excerpt") or src.get("label") or "")[:2000],
                retrieved_at=now,
            )

        review = BusinessClimateReview.objects.create(
            profile=profile,
            generated_at=now,
            confidence_score=result.get("confidence_score", 0),
            status="pending_review",
        )

        return {
            "profile_pk": str(profile.pk),
            "review_pk": str(review.pk),
            "status": "pending_review",
        }
    except Exception as exc:
        logger.exception(f"generate_business_climate_profile_task failed for {country_iso2}")
        raise self.retry(exc=exc, countdown=300)
