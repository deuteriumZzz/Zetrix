from django.conf import settings
from django.db import models
from apps.core.models import BaseModel


class Plan(BaseModel):
    """A subscription tier. Seeded via seed_plans management command — not
    user-creatable. Free tier limits apply when a user has no active
    UserSubscription."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    stripe_price_id = models.CharField(
        max_length=255, blank=True,
        help_text="Stripe Price ID (price_...) for the monthly subscription. Blank for the free plan.",
    )
    price_usd_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_active_alerts = models.PositiveIntegerField(
        default=1, help_text="Max active price-alert subscriptions. 0 = unlimited."
    )
    max_reports_per_month = models.PositiveIntegerField(
        default=1, help_text="Max reports generated per rolling 30 days. 0 = unlimited."
    )
    business_climate_access = models.BooleanField(
        default=False, help_text="Can view the Business layer's full scorecards."
    )
    is_default = models.BooleanField(
        default=False, help_text="Assigned to new users automatically (should be exactly one plan)."
    )

    class Meta:
        ordering = ["price_usd_monthly"]

    def __str__(self) -> str:
        return self.name


class UserSubscription(BaseModel):
    """Tracks a user's current plan and Stripe subscription state. Absence of
    a row (or status != 'active') means the user is on the default free plan."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("incomplete", "Incomplete"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_subscription"
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscribers")
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="incomplete")
    current_period_end = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.plan.name} ({self.status})"
