from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup
from django.db import IntegrityError
from django.urls import reverse

from apps.prices.models import PriceRecord
from apps.sources.models import ScrapeJob, Source
from apps.sources.scrapers.airbnb import AirbnbScraper
from apps.sources.scrapers.base import BaseScraper, ScrapedListing
from apps.sources.scrapers.booking import BookingScraper
from apps.sources.scrapers.factory import ScraperFactory
from apps.sources.services import ScrapingService
from apps.sources.views import SourceViewSet
from tests.factories import CountryFactory, RegionFactory, ScrapeJobFactory, SourceFactory

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class TestSourceModel:
    def test_str(self):
        region = RegionFactory(slug="canggu", name="Canggu")
        source = SourceFactory(
            name="Airbnb Canggu", source_type="airbnb", country=region.country, region=region
        )
        assert str(source) == "Airbnb Canggu (Canggu / airbnb)"

    def test_name_must_be_unique(self):
        SourceFactory(name="dup")
        with pytest.raises(IntegrityError):
            SourceFactory(name="dup")

    def test_defaults(self):
        source = SourceFactory()
        assert source.is_active is True
        assert source.check_in_offset_days == 7
        assert source.scrape_interval_hours == 24
        assert source.extra_config == {}


class TestScrapeJobModel:
    def test_default_status_is_pending(self):
        job = ScrapeJobFactory()
        assert job.status == "pending"
        assert job.records_fetched == 0

    def test_str_includes_source_and_status(self):
        source = SourceFactory(name="MySource")
        job = ScrapeJobFactory(source=source, status="success")
        assert "MySource" in str(job)
        assert "success" in str(job)


# ---------------------------------------------------------------------------
# Scraper parsing (no Playwright — HTML fixtures fed directly to _parse_html)
# ---------------------------------------------------------------------------


AIRBNB_CARD_HTML = """
<div data-testid="card-container">
  <a href="/rooms/123456?some=track"></a>
  <div data-testid="listing-card-name">Cozy Villa</div>
  <div>2.5 baths $150 per night 4.79 (28)</div>
</div>
"""

AIRBNB_CARD_NO_RATING_HTML = """
<div data-testid="card-container">
  <a href="/rooms/999"></a>
  <div data-testid="listing-card-name">No Rating Villa</div>
  <div>$80 per night</div>
</div>
"""

AIRBNB_CARD_MISSING_LINK_HTML = """
<div data-testid="card-container">
  <div data-testid="listing-card-name">No Link Villa</div>
  <div>$80 per night</div>
</div>
"""

BOOKING_CARD_HTML = """
<div data-testid="property-card">
  <div data-testid="title">Beach House</div>
  <div data-testid="price-and-discounted-price">$1,250</div>
  <div data-testid="review-score">Scored 8.7 | 342 reviews</div>
  <a data-testid="title-link" href="/hotel/id/beach-house.html?aid=xyz&label=abc"></a>
</div>
"""

BOOKING_CARD_MISSING_PRICE_HTML = """
<div data-testid="property-card">
  <div data-testid="title">No Price Hotel</div>
</div>
"""


class TestAirbnbScraperParsing:
    def _scraper(self):
        return AirbnbScraper(country=CountryFactory())

    def test_parses_price_and_distinguishes_rating_from_bath_count(self):
        soup = BeautifulSoup(AIRBNB_CARD_HTML, "lxml")
        listings = self._scraper()._parse_html(soup)
        assert len(listings) == 1
        listing = listings[0]
        assert listing.listing_id == "123456"
        assert listing.title == "Cozy Villa"
        assert listing.price_usd == 150.0
        # Regression: must pick up the rating "4.79", not the "2.5" from "2.5 baths".
        assert listing.rating == 4.79
        assert listing.reviews_count == 28
        assert listing.listing_url == "https://www.airbnb.com/rooms/123456"

    def test_missing_rating_defaults_to_none_and_zero_reviews(self):
        soup = BeautifulSoup(AIRBNB_CARD_NO_RATING_HTML, "lxml")
        listings = self._scraper()._parse_html(soup)
        assert len(listings) == 1
        assert listings[0].rating is None
        assert listings[0].reviews_count == 0

    def test_card_without_room_link_is_skipped(self):
        soup = BeautifulSoup(AIRBNB_CARD_MISSING_LINK_HTML, "lxml")
        listings = self._scraper()._parse_html(soup)
        assert listings == []

    def test_no_cards_returns_empty_list(self):
        soup = BeautifulSoup("<div>nothing here</div>", "lxml")
        assert self._scraper()._parse_html(soup) == []


class TestBookingScraperParsing:
    def _scraper(self):
        return BookingScraper(country=CountryFactory())

    def test_parses_price_rating_reviews_and_strips_affiliate_query(self):
        soup = BeautifulSoup(BOOKING_CARD_HTML, "lxml")
        listings = self._scraper()._parse_html(soup)
        assert len(listings) == 1
        listing = listings[0]
        assert listing.title == "Beach House"
        assert listing.price_usd == 1250.0
        assert listing.rating == 8.7
        assert listing.reviews_count == 342
        # Affiliate tracking query string must be stripped before storing.
        assert listing.listing_url == "/hotel/id/beach-house.html"
        assert "?" not in listing.listing_url
        assert listing.listing_id == "beach-house"

    def test_card_without_price_is_skipped(self):
        soup = BeautifulSoup(BOOKING_CARD_MISSING_PRICE_HTML, "lxml")
        listings = self._scraper()._parse_html(soup)
        assert listings == []


class TestScraperFactory:
    def test_create_returns_correct_class(self):
        region = RegionFactory(slug="canggu", name="Canggu")
        scraper = ScraperFactory.create("airbnb", country=region.country, region=region)
        assert isinstance(scraper, AirbnbScraper)
        assert scraper.region == region
        assert scraper.location_label == "Canggu"

    def test_create_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown source type"):
            ScraperFactory.create("nonexistent", country=CountryFactory())

    def test_register_adds_new_type(self):
        class DummyScraper(BaseScraper):
            source_type = "dummy"

            def fetch(self, check_in_offset_days=7):
                return []

        try:
            ScraperFactory.register("dummy", DummyScraper)
            assert "dummy" in ScraperFactory.available_types()
            scraper = ScraperFactory.create("dummy", country=CountryFactory())
            assert isinstance(scraper, DummyScraper)
        finally:
            from apps.sources.scrapers.factory import _REGISTRY

            _REGISTRY.pop("dummy", None)


class TestBaseScraperResilience:
    def test_run_swallows_fetch_exceptions_and_returns_empty_list(self):
        class BoomScraper(BaseScraper):
            source_type = "boom"

            def fetch(self, check_in_offset_days=7):
                raise RuntimeError("network blew up")

        scraper = BoomScraper(country=CountryFactory())
        assert scraper.run() == []

    def test_run_filters_out_non_positive_prices(self):
        class MixedScraper(BaseScraper):
            source_type = "mixed"

            def fetch(self, check_in_offset_days=7):
                return [
                    ScrapedListing(
                        listing_id="1", title="Good", price_usd=100.0, price_idr=None,
                        bedrooms=None, bathrooms=None, guests_capacity=None, rating=None,
                        reviews_count=0, listing_url="https://x/1",
                    ),
                    ScrapedListing(
                        listing_id="2", title="Zero price", price_usd=0.0, price_idr=None,
                        bedrooms=None, bathrooms=None, guests_capacity=None, rating=None,
                        reviews_count=0, listing_url="https://x/2",
                    ),
                ]

        scraper = MixedScraper(country=CountryFactory())
        results = scraper.run()
        assert len(results) == 1
        assert results[0].listing_id == "1"

    def test_fetch_rendered_html_without_context_raises(self):
        class NeedsContextScraper(BaseScraper):
            source_type = "needs-context"

            def fetch(self, check_in_offset_days=7):
                return self._fetch_rendered_html("https://example.com")

        scraper = NeedsContextScraper(country=CountryFactory())
        with pytest.raises(RuntimeError, match="context manager"):
            scraper._fetch_rendered_html("https://example.com")


# ---------------------------------------------------------------------------
# ScrapingService
# ---------------------------------------------------------------------------


class _FakeScraper:
    """Stand-in for a real BaseScraper: context-manager protocol, no Playwright."""

    def __init__(self, listings=None, raise_on_run=None):
        self._listings = listings or []
        self._raise = raise_on_run

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def run(self, check_in_offset_days=7):
        if self._raise:
            raise self._raise
        return self._listings


class TestScrapingService:
    def test_run_success_persists_records_and_marks_job_success(self):
        source = SourceFactory(source_type="airbnb", market_type="rental")
        listing = ScrapedListing(
            listing_id="abc", title="Nice place", price_usd=200.0, price_idr=None,
            bedrooms=2, bathrooms=1, guests_capacity=4, rating=4.5, reviews_count=10,
            listing_url="https://airbnb.com/rooms/abc",
        )
        fake = _FakeScraper(listings=[listing])
        with patch.object(ScraperFactory, "create", return_value=fake):
            job = ScrapingService(source).run()

        assert job.status == "success"
        assert job.records_fetched == 1
        assert job.started_at is not None
        assert job.finished_at is not None

        record = PriceRecord.objects.get(listing_id="abc")
        # country/region/market_type come from the Source, not the scraped listing.
        assert record.country == source.country
        assert record.region == source.region
        assert record.market_type == source.market_type
        assert record.price_usd == 200

    def test_run_failure_marks_job_failed_and_sets_error_message(self):
        source = SourceFactory()
        fake = _FakeScraper(raise_on_run=RuntimeError("boom"))
        with patch.object(ScraperFactory, "create", return_value=fake):
            job = ScrapingService(source).run()

        assert job.status == "failed"
        assert "boom" in job.error_message
        assert job.finished_at is not None
        assert PriceRecord.objects.count() == 0


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class TestSourceViewSet:
    def test_list_requires_authentication(self, api_client):
        resp = api_client.get(reverse("api_v1:source-list"))
        assert resp.status_code == 401

    def test_authenticated_list(self, auth_client):
        SourceFactory.create_batch(2)
        resp = auth_client.get(reverse("api_v1:source-list"))
        assert resp.status_code == 200
        assert resp.data["count"] == 2

    def test_by_region_filters_active_sources(self, auth_client):
        canggu = RegionFactory(slug="canggu", name="Canggu")
        ubud = RegionFactory(country=canggu.country, slug="ubud", name="Ubud")
        SourceFactory(country=canggu.country, region=canggu, is_active=True)
        SourceFactory(country=ubud.country, region=ubud, is_active=True)
        SourceFactory(country=canggu.country, region=canggu, is_active=False)
        resp = auth_client.get(
            reverse("api_v1:source-by-region"),
            {"country": canggu.country.iso2, "region": str(canggu.id)},
        )
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_trigger_action_queues_scrape_task(self, auth_client):
        """
        SourceViewSet.trigger_task is wired to scrape_source_task, so hitting
        /sources/{id}/trigger/ must queue a real scrape — matching what
        Airflow's DjangoAPIClient.trigger_scrape() expects. The task itself
        is mocked here so this stays a fast unit test (no real Celery/Playwright).
        """
        source = SourceFactory()
        mock_task = MagicMock()
        mock_task.delay.return_value = MagicMock(id="task-123")
        with patch.object(SourceViewSet, "trigger_task", mock_task):
            resp = auth_client.post(reverse("api_v1:source-trigger", args=[source.pk]))
        assert resp.status_code == 202
        assert resp.data["status"] == "queued"
        assert resp.data["task_id"] == "task-123"
        mock_task.delay.assert_called_once_with(str(source.pk))


class TestScrapeJobViewSet:
    def test_list_requires_authentication(self, api_client):
        resp = api_client.get(reverse("api_v1:scrape-job-list"))
        assert resp.status_code == 401

    def test_read_only(self, auth_client):
        source = SourceFactory()
        resp = auth_client.post(
            reverse("api_v1:scrape-job-list"), {"source": str(source.pk)}
        )
        assert resp.status_code == 405
