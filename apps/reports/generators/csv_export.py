from __future__ import annotations
import csv
import io
import logging
from pathlib import Path

from django.core.files.base import ContentFile

from .base import AbstractReportGenerator
from apps.prices.models import PriceRecord

logger = logging.getLogger(__name__)


class CSVReportGenerator(AbstractReportGenerator):

    def generate(self) -> Path:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow([
            "date", "region", "market_type", "property_type",
            "title", "price_usd", "bedrooms", "bathrooms",
            "guests_capacity", "rating", "reviews_count", "listing_url",
        ])

        records = PriceRecord.objects.select_related("country", "region").filter(
            scraped_at__date__range=(self.report.date_from, self.report.date_to),
        )
        if self.report.country:
            records = records.filter(country=self.report.country)
        if self.report.region:
            records = records.filter(region=self.report.region)
        if self.report.market_type:
            records = records.filter(market_type=self.report.market_type)
        records = records.order_by("scraped_at")

        for r in records:
            place = r.region.name if r.region else r.country.name
            writer.writerow([
                r.scraped_at.date(), place, r.market_type, r.property_type,
                r.title, r.price_usd, r.bedrooms, r.bathrooms,
                r.guests_capacity, r.rating, r.reviews_count, r.listing_url,
            ])

        filename = self._filename("csv")
        content = buffer.getvalue().encode("utf-8-sig")  # BOM for Excel
        self.report.file.save(filename, ContentFile(content), save=True)
        logger.info(f"CSV report generated: {filename}")
        return Path(self.report.file.path)
