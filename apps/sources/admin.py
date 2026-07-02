from django.contrib import admin
from .models import Source, ScrapeJob


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "market_type", "region", "is_active", "created_at")
    list_filter = ("source_type", "market_type", "region", "is_active")
    search_fields = ("name",)


@admin.register(ScrapeJob)
class ScrapeJobAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "records_fetched", "started_at", "finished_at")
    list_filter = ("status", "source__region")
    readonly_fields = ("created_at", "updated_at")
