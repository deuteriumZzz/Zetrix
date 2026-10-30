from rest_framework import serializers
from .models import AlertRule, NotificationLog, Subscription


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = "__all__"
        read_only_fields = ("id", "sent_at")


class SubscriptionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    country_flag = serializers.CharField(source="country.flag_emoji", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True, default=None)

    class Meta:
        model = Subscription
        fields = [
            "id", "username", "country", "country_name", "country_flag",
            "region", "region_name", "market_type",
            "threshold_pct", "direction", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "username", "created_at", "updated_at")
