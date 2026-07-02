from django.db import models
from apps.core.models import BaseModel


class SourceType(models.TextChoices):
    AIRBNB = "airbnb", "Airbnb"
    BOOKING = "booking", "Booking.com"
    AGODA = "agoda", "Agoda"
    MANUAL = "manual", "Manual"


class MarketType(models.TextChoices):
    RENTAL = "rental", "Short-term Rental"
    REAL_ESTATE = "real_estate", "Real Estate"


class Source(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    source_type = models.CharField(max_length=50, choices=SourceType.choices)
    market_type = models.CharField(
        max_length=50, choices=MarketType.choices, default=MarketType.RENTAL
    )
    country = models.ForeignKey("geo.Country", on_delete=models.PROTECT, related_name="sources")
    region = models.ForeignKey(
        "geo.Region", on_delete=models.PROTECT, null=True, blank=True, related_name="sources"
    )
    base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    check_in_offset_days = models.PositiveIntegerField(default=7)
    scrape_interval_hours = models.PositiveIntegerField(default=24)
    extra_config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["country", "source_type"]

    def __str__(self) -> str:
        place = self.region.name if self.region else self.country.name
        return f"{self.name} ({place} / {self.source_type})"


class ScrapeJob(BaseModel):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="jobs")
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        default="pending",
    )
    records_fetched = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Job {self.pk} — {self.source.name} [{self.status}]"
