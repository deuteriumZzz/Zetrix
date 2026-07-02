from django.contrib import admin
from .models import AlertRule, NotificationLog


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "market_type", "threshold_pct", "direction", "is_active")
    list_filter = ("is_active", "direction", "region")


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("channel", "is_success", "sent_at", "alert_rule")
    list_filter = ("channel", "is_success")
    readonly_fields = ("sent_at",)
