from rest_framework import serializers
from .models import Plan, UserSubscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id", "name", "slug", "price_usd_monthly",
            "max_active_alerts", "max_reports_per_month", "business_climate_access",
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = UserSubscription
        fields = ["id", "plan", "status", "current_period_end"]
