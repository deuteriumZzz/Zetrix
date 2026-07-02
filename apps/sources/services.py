from __future__ import annotations
import logging
from datetime import datetime, timezone

from django.db import transaction

from .models import Source, ScrapeJob
from .scrapers.factory import ScraperFactory

logger = logging.getLogger(__name__)


class ScrapingService:
    """Orchestrates scraping for a single Source."""

    def __init__(self, source: Source) -> None:
        self.source = source

    def run(self) -> ScrapeJob:
        job = ScrapeJob.objects.create(source=self.source)
        job.status = "running"
        job.started_at = datetime.now(tz=timezone.utc)
        job.save(update_fields=["status", "started_at"])

        try:
            scraper = ScraperFactory.create(
                source_type=self.source.source_type,
                country=self.source.country,
                region=self.source.region,
                config=self.source.extra_config,
            )
            with scraper:
                listings = scraper.run(
                    check_in_offset_days=self.source.check_in_offset_days
                )
            self._persist_listings(listings, job)
            job.status = "success"
            job.records_fetched = len(listings)
        except Exception as exc:
            logger.exception(f"ScrapingService failed for source {self.source.pk}")
            job.status = "failed"
            job.error_message = str(exc)
        finally:
            job.finished_at = datetime.now(tz=timezone.utc)
            job.save(update_fields=["status", "records_fetched", "finished_at", "error_message"])

        return job

    @transaction.atomic
    def _persist_listings(self, listings, job: ScrapeJob) -> None:
        from apps.prices.models import PriceRecord
        from datetime import datetime, timezone

        records = [
            PriceRecord(
                source=self.source,
                country=self.source.country,
                region=self.source.region,
                market_type=self.source.market_type,
                listing_id=listing.listing_id,
                title=listing.title,
                price_usd=listing.price_usd,
                price_idr=listing.price_idr,
                bedrooms=listing.bedrooms,
                bathrooms=listing.bathrooms,
                guests_capacity=listing.guests_capacity,
                rating=listing.rating,
                reviews_count=listing.reviews_count,
                listing_url=listing.listing_url,
                scraped_at=listing.scraped_at or datetime.now(tz=timezone.utc),
                raw_data=listing.raw_data,
            )
            for listing in listings
        ]
        PriceRecord.objects.bulk_create(records, ignore_conflicts=True)
