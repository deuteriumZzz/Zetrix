from django.conf import settings
from django.db import models
from apps.core.models import BaseModel


class UserProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    telegram_chat_id = models.CharField(
        max_length=50, unique=True, blank=True, null=True,
        help_text="Telegram chat ID for bot notifications"
    )
    telegram_username = models.CharField(max_length=150, blank=True)
    preferred_country = models.ForeignKey(
        "geo.Country", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    preferred_region = models.ForeignKey(
        "geo.Region", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    preferred_market_type = models.CharField(
        max_length=20,
        choices=[("rental", "Rental"), ("real_estate", "Real Estate")],
        default="rental",
    )

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"Profile({self.user.username})"
