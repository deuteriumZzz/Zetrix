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

    class Meta:
        model = Subscription
        fields = [
            "id", "username", "country", "region", "market_type",
            "threshold_pct", "direction", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ("id", "username", "created_at", "updated_at")
