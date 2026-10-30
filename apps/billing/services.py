from __future__ import annotations
from datetime import timedelta
from django.utils import timezone
from .models import Plan, UserSubscription


def get_plan_for_user(user) -> Plan:
    """Returns the user's active plan, falling back to the default (free) plan."""
    sub = UserSubscription.objects.filter(user=user, status="active").select_related("plan").first()
    if sub:
        return sub.plan
    return Plan.objects.filter(is_default=True).first() or Plan.objects.order_by("price_usd_monthly").first()


def can_create_alert(user) -> tuple[bool, str]:
    from apps.notifications.models import Subscription
    plan = get_plan_for_user(user)
    if plan.max_active_alerts == 0:
        return True, ""
    active_count = Subscription.objects.filter(user=user, is_active=True).count()
    if active_count >= plan.max_active_alerts:
        return False, f"Your {plan.name} plan allows up to {plan.max_active_alerts} active alert(s). Upgrade for more."
    return True, ""


def can_create_report(user) -> tuple[bool, str]:
    from apps.reports.models import Report
    plan = get_plan_for_user(user)
    if plan.max_reports_per_month == 0:
        return True, ""
    since = timezone.now() - timedelta(days=30)
    recent_count = Report.objects.filter(requested_by=user, created_at__gte=since).count()
    if recent_count >= plan.max_reports_per_month:
        return False, f"Your {plan.name} plan allows {plan.max_reports_per_month} report(s) per 30 days. Upgrade for more."
    return True, ""
