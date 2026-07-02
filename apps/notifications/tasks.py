from __future__ import annotations
import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def check_subscriptions_task(self) -> dict:
    """Check all active subscriptions against today's DailyAggregates and fire alerts."""
    from .models import Subscription, NotificationLog
    from apps.prices.models import DailyAggregate
    from apps.notifications.senders.telegram import TelegramSender

    today = date.today()
    sent = 0
    skipped = 0

    active_subs = (
        Subscription.objects
        .filter(is_active=True)
        .select_related("user__profile", "country", "region")
    )

    # Batch-load today's aggregates into a lookup dict
    agg_map = {
        (a.country_id, a.region_id, a.market_type): a
        for a in DailyAggregate.objects.filter(date=today)
    }

    for sub in active_subs:
        agg = agg_map.get((sub.country_id, sub.region_id, sub.market_type))
        if not agg or agg.price_change_pct is None:
            skipped += 1
            continue

        change = float(agg.price_change_pct)
        threshold = float(sub.threshold_pct)

        triggered = (
            (sub.direction == "up" and change >= threshold)
            or (sub.direction == "down" and change <= -threshold)
            or (sub.direction == "any" and abs(change) >= threshold)
        )

        if not triggered:
            skipped += 1
            continue

        chat_id = None
        try:
            chat_id = sub.user.profile.telegram_chat_id
        except Exception:
            pass

        if not chat_id:
            logger.warning(f"Subscription {sub.pk}: user has no telegram_chat_id, skipping")
            skipped += 1
            continue

        place = sub.region.name if sub.region else sub.country.name
        sender = TelegramSender(chat_id=chat_id)
        success = sender.send_price_alert(
            region=place,
            market_type=sub.market_type,
            change_pct=change,
            avg_price=float(agg.avg_price_usd),
            threshold_pct=threshold,
        )

        NotificationLog.objects.create(
            channel="telegram",
            message=f"Alert for {place}/{sub.market_type}: {change:+.1f}%",
            is_success=success,
            error="" if success else "Send failed",
        )

        if success:
            sent += 1
        else:
            skipped += 1

    logger.info(f"check_subscriptions_task: sent={sent}, skipped={skipped}")
    return {"sent": sent, "skipped": skipped, "date": str(today)}
