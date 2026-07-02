from django.db import models
from apps.core.models import BaseModel
from apps.sources.models import MarketType


class ReportFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    CSV = "csv", "CSV"


class ReportStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class Report(BaseModel):
    title = models.CharField(max_length=255)
    country = models.ForeignKey(
        "geo.Country", on_delete=models.PROTECT, null=True, blank=True, related_name="reports"
    )
    region = models.ForeignKey(
        "geo.Region", on_delete=models.PROTECT, null=True, blank=True, related_name="reports"
    )
    market_type = models.CharField(max_length=50, choices=MarketType.choices, blank=True)
    date_from = models.DateField()
    date_to = models.DateField()
    format = models.CharField(max_length=10, choices=ReportFormat.choices, default=ReportFormat.PDF)
    status = models.CharField(
        max_length=20, choices=ReportStatus.choices, default=ReportStatus.PENDING
    )
    file = models.FileField(upload_to="reports/%Y/%m/", blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reports"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"
