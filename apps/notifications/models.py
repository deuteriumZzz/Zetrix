from django.conf import settings
from django.db import models
from apps.core.models import BaseModel


class AlertRule(BaseModel):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(
        "geo.Country", on_delete=models.PROTECT, null=True, blank=True, related_name="alert_rules"
    )
    region = models.ForeignKey(
        "geo.Region", on_delete=models.PROTECT, null=True, blank=True, related_name="alert_rules"
    )
    market_type = models.CharField(max_length=50, blank=True)
    threshold_pct = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Trigger when price changes by this % or more"
    )
    direction = models.CharField(
        max_length=10,
        choices=[("up", "Price Up"), ("down", "Price Down"), ("any", "Any Change")],
        default="any",
    )
    is_active = models.BooleanField(default=True)
    notify_telegram = models.BooleanField(default=True)

    def __str__(self) -> str:
        place = self.region.name if self.region else (self.country.name if self.country else "Any")
        return f"{self.name} ({place}, >{self.threshold_pct}%)"


class NotificationLog(BaseModel):
    alert_rule = models.ForeignKey(
        AlertRule, on_delete=models.SET_NULL, null=True, blank=True, related_name="logs"
    )
    channel = models.CharField(max_length=50)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_success = models.BooleanField(default=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_at"]


class Subscription(BaseModel):
    """A user-configured price alert for a specific region/market."""

    DIRECTION_CHOICES = [("up", "Price Up"), ("down", "Price Down"), ("any", "Any Change")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    country = models.ForeignKey("geo.Country", on_delete=models.CASCADE, related_name="subscriptions")
    region = models.ForeignKey(
        "geo.Region", on_delete=models.CASCADE, null=True, blank=True, related_name="subscriptions"
    )
    market_type = models.CharField(
        max_length=20,
        choices=[("rental", "Rental"), ("real_estate", "Real Estate")],
        default="rental",
    )
    threshold_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=5.0,
        help_text="Alert when price changes by this % or more"
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default="any")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "country", "region", "market_type")
        ordering = ["country", "market_type"]

    def __str__(self) -> str:
        place = self.region.name if self.region else self.country.name
        return f"{self.user.username} -> {place}/{self.market_type} (>{self.threshold_pct}%)"
