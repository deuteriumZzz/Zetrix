from datetime import date, timedelta

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from apps.prices.models import DailyAggregate, PriceRecord
from apps.prices.services import PriceAnalysisService
from tests.factories import (
    CountryFactory,
    DailyAggregateFactory,
    PriceRecordFactory,
    RegionFactory,
    SourceFactory,
)

pytestmark = pytest.mark.django_db


class TestPriceRecordModel:
    def test_str(self):
        record = PriceRecordFactory(property_type="villa", price_usd="123.45")
        assert str(record) == "Canggu / villa — $123.45"


class TestDailyAggregateModel:
    def test_unique_together_date_region_market_property(self):
        DailyAggregateFactory(
            date=date(2026, 1, 1), market_type="rental", property_type="villa"
        )
        with pytest.raises(IntegrityError):
            DailyAggregateFactory(
                date=date(2026, 1, 1), market_type="rental", property_type="villa"
            )


class TestPriceAnalysisServiceComputeAggregates:
    def test_no_records_creates_no_aggregate(self):
        target = date(2026, 3, 1)
        PriceAnalysisService.compute_daily_aggregates(target)
        assert DailyAggregate.objects.count() == 0

    def test_computes_avg_min_max_median(self):
        region = RegionFactory(slug="canggu", name="Canggu")
        source = SourceFactory(country=region.country, region=region, market_type="rental")
        target = date(2026, 3, 1)
        scraped_at = timezone.make_aware(timezone.datetime(2026, 3, 1, 12, 0, 0))
        for price in ["100.00", "200.00", "300.00"]:
            PriceRecordFactory(
                source=source, country=region.country, region=region, market_type="rental",
                property_type="villa", price_usd=price, scraped_at=scraped_at,
            )

        PriceAnalysisService.compute_daily_aggregates(target)

        agg = DailyAggregate.objects.get(
            date=target, country=region.country, region=region,
            market_type="rental", property_type="villa",
        )
        assert agg.avg_price_usd == 200
        assert agg.min_price_usd == 100
        assert agg.max_price_usd == 300
        assert agg.median_price_usd == 200
        assert agg.listings_count == 3
        assert agg.price_change_pct is None  # no previous day aggregate

    def test_price_change_pct_vs_previous_day(self):
        region = RegionFactory(slug="canggu", name="Canggu")
        source = SourceFactory(country=region.country, region=region, market_type="rental")
        yesterday = date(2026, 3, 1)
        today = date(2026, 3, 2)

        DailyAggregateFactory(
            date=yesterday, country=region.country, region=region,
            market_type="rental", property_type="villa", avg_price_usd="100.00",
        )
        scraped_at = timezone.make_aware(timezone.datetime(2026, 3, 2, 12, 0, 0))
        PriceRecordFactory(
            source=source, country=region.country, region=region, market_type="rental",
            property_type="villa", price_usd="150.00", scraped_at=scraped_at,
        )

        PriceAnalysisService.compute_daily_aggregates(today)

        agg = DailyAggregate.objects.get(date=today, region=region, property_type="villa")
        assert agg.price_change_pct == 50.0  # (150-100)/100 * 100

    def test_idempotent_when_run_twice(self):
        region = RegionFactory(slug="ubud", name="Ubud")
        source = SourceFactory(country=region.country, region=region, market_type="rental")
        target = date(2026, 3, 5)
        scraped_at = timezone.make_aware(timezone.datetime(2026, 3, 5, 9, 0, 0))
        PriceRecordFactory(
            source=source, country=region.country, region=region, market_type="rental",
            property_type="villa", price_usd="90.00", scraped_at=scraped_at,
        )

        PriceAnalysisService.compute_daily_aggregates(target)
        PriceAnalysisService.compute_daily_aggregates(target)

        assert DailyAggregate.objects.filter(date=target, region=region).count() == 1


class TestPriceAnalysisServiceGetTrend:
    def test_returns_aggregates_within_window_ordered_by_date(self):
        region = RegionFactory(slug="canggu", name="Canggu")
        DailyAggregateFactory(
            date=date.today() - timedelta(days=1), country=region.country, region=region,
            market_type="rental",
        )
        DailyAggregateFactory(
            date=date.today() - timedelta(days=100), country=region.country, region=region,
            market_type="rental",
        )
        result = PriceAnalysisService.get_trend(
            country=region.country, region=region, market_type="rental", days=30
        )
        assert len(result) == 1


class TestPriceViews:
    def test_records_list_requires_auth(self, api_client):
        resp = api_client.get(reverse("api_v1:price-record-list"))
        assert resp.status_code == 401

    def test_trend_requires_country(self, auth_client):
        resp = auth_client.get(reverse("api_v1:price-record-trend"), {"days": "30"})
        assert resp.status_code == 400

    def test_trend_rejects_non_integer_days(self, auth_client):
        country = CountryFactory()
        resp = auth_client.get(
            reverse("api_v1:price-record-trend"), {"country": country.iso2, "days": "abc"}
        )
        assert resp.status_code == 400

    def test_trend_rejects_out_of_range_days(self, auth_client):
        country = CountryFactory()
        resp = auth_client.get(
            reverse("api_v1:price-record-trend"), {"country": country.iso2, "days": "9999"}
        )
        assert resp.status_code == 400

    def test_trend_returns_data_within_range(self, auth_client):
        region = RegionFactory(slug="canggu", name="Canggu")
        DailyAggregateFactory(
            date=date.today(), country=region.country, region=region, market_type="rental",
        )
        resp = auth_client.get(
            reverse("api_v1:price-record-trend"),
            {"country": region.country.iso2, "region": str(region.id), "days": "30"},
        )
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_aggregates_list_requires_auth(self, api_client):
        resp = api_client.get(reverse("api_v1:daily-aggregate-list"))
        assert resp.status_code == 401
