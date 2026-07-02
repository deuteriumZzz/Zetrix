from django.contrib import admin
from .models import PriceRecord, DailyAggregate


@admin.register(PriceRecord)
class PriceRecordAdmin(admin.ModelAdmin):
    list_display = ("region", "property_type", "price_usd", "source", "scraped_at")
    list_filter = ("region", "market_type", "property_type")
    search_fields = ("listing_id", "title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DailyAggregate)
class DailyAggregateAdmin(admin.ModelAdmin):
    list_display = ("date", "region", "market_type", "avg_price_usd", "listings_count", "price_change_pct")
    list_filter = ("region", "market_type", "property_type")
