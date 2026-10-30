from datetime import date, timedelta
from django.db.models import Avg, Min, Max
from .models import DailyAggregate


class PriceAnalysisService:

    @staticmethod
    def get_trend(country, region, market_type: str, days: int = 30) -> list[dict]:
        start_date = date.today() - timedelta(days=days)
        rows = (
            DailyAggregate.objects
            .filter(country=country, region=region, market_type=market_type, date__gte=start_date)
            .order_by("date")
            .values("date", "avg_price_usd", "price_change_pct", "listings_count")
        )

        # A date can have multiple rows (one per property_type) — collapse to a
        # single listings-weighted point per date so the trend line/chart is clean.
        by_date: dict = {}
        for row in rows:
            bucket = by_date.setdefault(row["date"], {"weighted_sum": 0.0, "listings_count": 0, "changes": []})
            count = row["listings_count"] or 0
            bucket["weighted_sum"] += float(row["avg_price_usd"]) * count
            bucket["listings_count"] += count
            if row["price_change_pct"] is not None:
                bucket["changes"].append(float(row["price_change_pct"]))

        result = []
        for day in sorted(by_date):
            bucket = by_date[day]
            avg_price = bucket["weighted_sum"] / bucket["listings_count"] if bucket["listings_count"] else 0
            avg_change = sum(bucket["changes"]) / len(bucket["changes"]) if bucket["changes"] else None
            result.append({
                "date": day,
                "avg_price_usd": round(avg_price, 2),
                "price_change_pct": round(avg_change, 2) if avg_change is not None else None,
                "listings_count": bucket["listings_count"],
            })
        return result

    @staticmethod
    def compute_daily_aggregates(target_date: date) -> None:
        from apps.prices.models import PriceRecord, DailyAggregate, PropertyType
        import statistics
        from collections import defaultdict

        # Single query for all records on target_date — eliminates 48+ DB round trips.
        records_qs = PriceRecord.objects.filter(
            scraped_at__date=target_date,
        ).values("country_id", "region_id", "market_type", "property_type", "price_usd")

        # Group in Python — per (country, region) and also rolled up per country
        # (region=None) so country-level views work even when all underlying
        # PriceRecords are tagged with a region (e.g. Bali's Canggu/Ubud/...).
        groups: dict[tuple, list[float]] = defaultdict(list)
        for row in records_qs:
            key = (row["country_id"], row["region_id"], row["market_type"], row["property_type"])
            groups[key].append(float(row["price_usd"]))
            country_key = (row["country_id"], None, row["market_type"], row["property_type"])
            groups[country_key].append(float(row["price_usd"]))

        if not groups:
            return

        # Fetch previous day aggregates in one query
        prev_aggs = {
            (a.country_id, a.region_id, a.market_type, a.property_type): a
            for a in DailyAggregate.objects.filter(date=target_date - timedelta(days=1))
        }

        for (country_id, region_id, market_type, prop_type), prices in groups.items():
            avg_price = sum(prices) / len(prices)
            median_price = statistics.median(prices)

            prev = prev_aggs.get((country_id, region_id, market_type, prop_type))
            change_pct = None
            if prev and prev.avg_price_usd:
                change_pct = round(
                    (avg_price - float(prev.avg_price_usd)) / float(prev.avg_price_usd) * 100, 2
                )

            DailyAggregate.objects.update_or_create(
                date=target_date,
                country_id=country_id,
                region_id=region_id,
                market_type=market_type,
                property_type=prop_type,
                defaults={
                    "avg_price_usd": round(avg_price, 2),
                    "min_price_usd": min(prices),
                    "max_price_usd": max(prices),
                    "median_price_usd": round(median_price, 2),
                    "listings_count": len(prices),
                    "price_change_pct": change_pct,
                },
            )
