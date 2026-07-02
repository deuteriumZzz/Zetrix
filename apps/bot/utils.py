from __future__ import annotations
import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

PAGE_SIZE = 8


@sync_to_async
def ensure_profile(telegram_chat_id: str, telegram_username: str = "") -> None:
    """Get or create a User + UserProfile for a Telegram user."""
    from django.contrib.auth import get_user_model
    from apps.users.models import UserProfile

    User = get_user_model()
    profile = UserProfile.objects.filter(telegram_chat_id=telegram_chat_id).first()
    if not profile:
        user, _ = User.objects.get_or_create(
            username=f"tg_{telegram_chat_id}",
            defaults={"is_active": True},
        )
        UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "telegram_chat_id": telegram_chat_id,
                "telegram_username": telegram_username,
            },
        )


@sync_to_async
def nearest_location(lat: float, lon: float) -> dict | None:
    """Nearest Region (if any exist) else nearest Country, by naive
    Euclidean distance over centroids — cheap at ~200-row scale, called
    rarely (only on a shared-location message)."""
    import math

    from apps.geo.models import Country, Region

    def dist(clat, clng):
        return math.sqrt((lat - clat) ** 2 + (lon - clng) ** 2)

    best_region = min(
        Region.objects.all(), key=lambda r: dist(r.centroid_lat, r.centroid_lng), default=None
    )
    best_country = min(
        Country.objects.all(), key=lambda c: dist(c.centroid_lat, c.centroid_lng), default=None
    )
    if best_region is None and best_country is None:
        return None
    if best_region is not None and dist(best_region.centroid_lat, best_region.centroid_lng) <= dist(
        best_country.centroid_lat, best_country.centroid_lng
    ):
        return {"country_iso2": best_region.country.iso2, "region_slug": best_region.slug,
                "label": best_region.name}
    return {"country_iso2": best_country.iso2, "region_slug": None, "label": best_country.name}


@sync_to_async
def get_continents() -> list[dict]:
    from apps.geo.models import Continent
    return list(Continent.objects.order_by("name").values("code", "name"))


@sync_to_async
def get_countries_page(continent_code: str, page: int = 0) -> dict:
    from apps.geo.models import Country

    qs = Country.objects.filter(continent__code=continent_code).order_by("name")
    total = qs.count()
    start = page * PAGE_SIZE
    items = list(qs[start:start + PAGE_SIZE].values("iso2", "name", "flag_emoji"))
    return {"items": items, "page": page, "has_next": start + PAGE_SIZE < total, "has_prev": page > 0}


@sync_to_async
def search_countries(query: str, limit: int = 8) -> list[dict]:
    from apps.geo.models import Country
    return list(
        Country.objects.filter(name__icontains=query.strip())
        .order_by("name")[:limit]
        .values("iso2", "name", "flag_emoji")
    )


@sync_to_async
def get_country_and_regions(iso2: str) -> dict | None:
    from apps.geo.models import Country

    country = Country.objects.filter(iso2=iso2.upper()).first()
    if not country:
        return None
    regions = list(country.regions.filter(parent__isnull=False).order_by("name").values("slug", "name"))
    return {"iso2": country.iso2, "name": country.name, "flag_emoji": country.flag_emoji, "regions": regions}


@sync_to_async
def get_latest_prices(country_iso2: str, region_slug: str | None, market_type: str = "rental") -> dict | None:
    from datetime import date, timedelta
    from apps.prices.models import DailyAggregate

    for delta in range(7):
        target = date.today() - timedelta(days=delta)
        agg = (
            DailyAggregate.objects
            .filter(
                country__iso2=country_iso2.upper(),
                region__slug=region_slug if region_slug else None,
                market_type=market_type, date=target,
            )
            .first()
        )
        if agg:
            return {
                "date": str(agg.date),
                "avg": float(agg.avg_price_usd),
                "min": float(agg.min_price_usd),
                "max": float(agg.max_price_usd),
                "count": agg.listings_count,
                "change": float(agg.price_change_pct) if agg.price_change_pct else None,
            }
    return None


@sync_to_async
def list_subscriptions(telegram_chat_id: str) -> list[dict]:
    from apps.users.models import UserProfile
    from apps.notifications.models import Subscription

    try:
        profile = UserProfile.objects.get(telegram_chat_id=telegram_chat_id)
    except UserProfile.DoesNotExist:
        return []
    return [
        {
            "country_iso2": s.country.iso2,
            "region_name": s.region.name if s.region else None,
            "label": s.region.name if s.region else s.country.name,
            "market_type": s.market_type,
            "threshold_pct": s.threshold_pct,
            "direction": s.direction,
        }
        for s in Subscription.objects.filter(user=profile.user, is_active=True).select_related(
            "country", "region"
        )
    ]


@sync_to_async
def toggle_subscription(telegram_chat_id: str, country_iso2: str, region_slug: str | None, activate: bool) -> str:
    from apps.geo.models import Country, Region
    from apps.users.models import UserProfile
    from apps.notifications.models import Subscription

    try:
        profile = UserProfile.objects.get(telegram_chat_id=telegram_chat_id)
    except UserProfile.DoesNotExist:
        return "no_profile"

    country = Country.objects.filter(iso2=country_iso2.upper()).first()
    if not country:
        return "unknown_location"
    region = Region.objects.filter(country=country, slug=region_slug).first() if region_slug else None

    if activate:
        sub, created = Subscription.objects.get_or_create(
            user=profile.user,
            country=country,
            region=region,
            market_type="rental",
            defaults={"threshold_pct": 5.0, "direction": "any", "is_active": True},
        )
        if not created and not sub.is_active:
            sub.is_active = True
            sub.save(update_fields=["is_active"])
        return "subscribed"
    else:
        Subscription.objects.filter(
            user=profile.user, country=country, region=region, is_active=True
        ).update(is_active=False)
        return "unsubscribed"


@sync_to_async
def request_report(telegram_chat_id: str, country_iso2: str, region_slug: str | None) -> str:
    from datetime import date, timedelta

    from apps.geo.models import Country, Region
    from apps.reports.models import Report, ReportFormat, ReportStatus
    from apps.reports.tasks import generate_report_task

    country = Country.objects.filter(iso2=country_iso2.upper()).first()
    if not country:
        return ""
    region = Region.objects.filter(country=country, slug=region_slug).first() if region_slug else None
    label = region.name if region else country.name

    date_to = date.today()
    date_from = date_to - timedelta(days=30)

    report = Report.objects.create(
        title=f"Market Report — {label} (30d)",
        country=country,
        region=region,
        market_type="rental",
        date_from=date_from,
        date_to=date_to,
        format=ReportFormat.PDF,
        status=ReportStatus.PENDING,
    )
    generate_report_task.delay(str(report.pk), notify_chat_id=telegram_chat_id)
    return str(report.pk)
