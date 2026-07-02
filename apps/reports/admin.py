from django.contrib import admin
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "region", "market_type", "format", "status", "generated_at")
    list_filter = ("status", "format", "region", "market_type")
    readonly_fields = ("created_at", "updated_at", "generated_at")
