from django.db import models
from apps.core.models import BaseModel
from apps.sources.models import Source, MarketType


class PropertyType(models.TextChoices):
    VILLA = "villa", "Villa"
    APARTMENT = "apartment", "Apartment"
    HOUSE = "house", "House"
    ROOM = "room", "Room"


class PriceRecord(BaseModel):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="price_records")
    country = models.ForeignKey("geo.Country", on_delete=models.PROTECT, related_name="price_records")
    region = models.ForeignKey(
        "geo.Region", on_delete=models.PROTECT, null=True, blank=True, related_name="price_records"
    )
    market_type = models.CharField(max_length=50, choices=MarketType.choices)
    property_type = models.CharField(
        max_length=50, choices=PropertyType.choices, default=PropertyType.VILLA
    )
    listing_id = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=500, blank=True)
    price_usd = models.DecimalField(max_digits=12, decimal_places=2)
    price_idr = models.DecimalField(max_digits=18, decimal_places=0, null=True, blank=True)
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    guests_capacity = models.PositiveSmallIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    reviews_count = models.PositiveIntegerField(default=0)
    listing_url = models.URLField(blank=True)
    scraped_at = models.DateTimeField()
    raw_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-scraped_at"]
        indexes = [
            models.Index(fields=["country", "region", "market_type", "scraped_at"]),
            models.Index(fields=["source", "scraped_at"]),
        ]

    def __str__(self) -> str:
        place = self.region.name if self.region else self.country.name
        return f"{place} / {self.property_type} — ${self.price_usd}"


class DailyAggregate(BaseModel):
    """Pre-computed daily stats per region & market type for fast charting."""

    date = models.DateField()
    country = models.ForeignKey("geo.Country", on_delete=models.PROTECT, related_name="daily_aggregates")
    region = models.ForeignKey(
        "geo.Region", on_delete=models.PROTECT, null=True, blank=True, related_name="daily_aggregates"
    )
    market_type = models.CharField(max_length=50, choices=MarketType.choices)
    property_type = models.CharField(max_length=50, choices=PropertyType.choices)
    avg_price_usd = models.DecimalField(max_digits=12, decimal_places=2)
    min_price_usd = models.DecimalField(max_digits=12, decimal_places=2)
    max_price_usd = models.DecimalField(max_digits=12, decimal_places=2)
    median_price_usd = models.DecimalField(max_digits=12, decimal_places=2)
    listings_count = models.PositiveIntegerField()
    price_change_pct = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text="% change vs previous day"
    )

    class Meta:
        unique_together = ("date", "country", "region", "market_type", "property_type")
        ordering = ["-date"]

    def __str__(self) -> str:
        place = self.region.name if self.region else self.country.name
        return f"{self.date} | {place} | avg ${self.avg_price_usd}"
