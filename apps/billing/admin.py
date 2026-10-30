from django.contrib import admin
from .models import Plan, UserSubscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price_usd_monthly", "max_active_alerts", "max_reports_per_month", "business_climate_access", "is_default")


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("user__username", "stripe_customer_id")
