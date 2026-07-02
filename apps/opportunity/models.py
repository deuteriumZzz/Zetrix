from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class BusinessClimateProfile(BaseModel):
    """Business/legal-complexity data for a country, with an optional
    region-level override (national law almost always governs land
    ownership/tax/registration/visas, but a region override is supported
    for the rare case of a special economic zone or similar)."""

    country = models.ForeignKey(
        "geo.Country", on_delete=models.CASCADE, related_name="business_climate_profiles"
    )
    region = models.ForeignKey(
        "geo.Region", on_delete=models.CASCADE, null=True, blank=True,
        related_name="business_climate_profiles",
    )

    foreign_land_ownership_summary = models.TextField(blank=True)
    foreign_land_ownership_score = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="0-100, higher = easier for foreigners to own land"
    )

    business_registration_summary = models.TextField(blank=True)
    business_registration_days_estimate = models.PositiveIntegerField(null=True, blank=True)
    business_registration_cost_usd_estimate = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    business_registration_score = models.PositiveSmallIntegerField(null=True, blank=True)

    tax_overview_summary = models.TextField(blank=True)
    corporate_tax_rate_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    personal_income_tax_top_rate_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    investor_visa_summary = models.TextField(blank=True)
    has_digital_nomad_visa = models.BooleanField(default=False)
    has_investor_residency_program = models.BooleanField(default=False)

    overall_complexity_score = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="0-100 weighted composite, higher = more opportunity-friendly"
    )

    published_review = models.ForeignKey(
        "BusinessClimateReview", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )

    class Meta:
        unique_together = ("country", "region")
        ordering = ["country", "region"]

    def __str__(self) -> str:
        place = self.region.name if self.region else self.country.name
        return f"Business climate: {place}"

    @property
    def is_published(self) -> bool:
        return self.published_review_id is not None


class ClimateDataSourceType(models.TextChoices):
    LLM_GENERATED = "llm_generated", "LLM Generated"
    HERITAGE_ECON_FREEDOM = "heritage_econ_freedom", "Heritage Index of Economic Freedom"
    PROPERTY_RIGHTS_ALLIANCE = "property_rights_alliance", "Property Rights Alliance IPRI"
    OECD_FDI_INDEX = "oecd_fdi_index", "OECD FDI Regulatory Restrictiveness Index"
    MANUAL = "manual", "Manual"


class ClimateDataSource(BaseModel):
    """One citation backing a BusinessClimateProfile — a profile can have
    multiple, mixing LLM-derived and index-derived citations."""

    profile = models.ForeignKey(BusinessClimateProfile, on_delete=models.CASCADE, related_name="sources")
    source_type = models.CharField(max_length=30, choices=ClimateDataSourceType.choices)
    citation_url = models.URLField(blank=True)
    raw_excerpt = models.TextField(blank=True)
    retrieved_at = models.DateTimeField()

    class Meta:
        ordering = ["-retrieved_at"]

    def __str__(self) -> str:
        return f"{self.get_source_type_display()} for {self.profile_id}"


class BusinessClimateReviewStatus(models.TextChoices):
    PENDING_REVIEW = "pending_review", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    NEEDS_REVISION = "needs_revision", "Needs Revision"


class BusinessClimateReview(BaseModel):
    """Human-review/approval gate. A BusinessClimateProfile is only visible
    via the public API once it has an APPROVED review referenced by
    profile.published_review — regenerating a profile creates a fresh
    PENDING_REVIEW row without un-publishing the previously-approved one."""

    profile = models.ForeignKey(BusinessClimateProfile, on_delete=models.CASCADE, related_name="reviews")
    generated_at = models.DateTimeField()
    confidence_score = models.PositiveSmallIntegerField(help_text="0-100, LLM self-reported/heuristic")
    status = models.CharField(
        max_length=20, choices=BusinessClimateReviewStatus.choices,
        default=BusinessClimateReviewStatus.PENDING_REVIEW,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return f"Review {self.pk} [{self.status}]"
