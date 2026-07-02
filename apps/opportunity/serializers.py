from rest_framework import serializers

from .models import BusinessClimateProfile, BusinessClimateReview, ClimateDataSource


class ClimateDataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClimateDataSource
        fields = ["id", "source_type", "citation_url", "raw_excerpt", "retrieved_at"]


class BusinessClimateProfileSerializer(serializers.ModelSerializer):
    """Public representation — only ever served for published profiles."""

    sources = ClimateDataSourceSerializer(many=True, read_only=True)
    country_iso2 = serializers.CharField(source="country.iso2", read_only=True)
    last_reviewed_at = serializers.SerializerMethodField()

    class Meta:
        model = BusinessClimateProfile
        fields = [
            "id", "country_iso2", "region",
            "foreign_land_ownership_summary", "foreign_land_ownership_score",
            "business_registration_summary", "business_registration_days_estimate",
            "business_registration_cost_usd_estimate", "business_registration_score",
            "tax_overview_summary", "corporate_tax_rate_pct", "personal_income_tax_top_rate_pct",
            "investor_visa_summary", "has_digital_nomad_visa", "has_investor_residency_program",
            "overall_complexity_score", "sources", "last_reviewed_at",
        ]

    def get_last_reviewed_at(self, obj):
        return obj.published_review.reviewed_at if obj.published_review else None


class BusinessClimateReviewSerializer(serializers.ModelSerializer):
    profile_label = serializers.CharField(source="profile.__str__", read_only=True)

    class Meta:
        model = BusinessClimateReview
        fields = [
            "id", "profile", "profile_label", "generated_at", "confidence_score",
            "status", "reviewed_by", "reviewed_at", "review_notes",
        ]
        read_only_fields = ("id", "profile", "generated_at", "confidence_score", "reviewed_by", "reviewed_at")
