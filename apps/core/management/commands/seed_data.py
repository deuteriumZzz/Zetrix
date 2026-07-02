"""
Seed realistic test data for Bali Market Analyzer.

Usage:
  python manage.py seed_data            # 30 days, all Bali regions
  python manage.py seed_data --days 7   # last 7 days only
  python manage.py seed_data --clear    # wipe and re-seed

Requires `python manage.py seed_geo` (world countries) and the Bali
data migration (apps.geo's Indonesia/Bali/6-region hierarchy) to have
already run — this command only seeds price demo data, not geography.
"""
import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


# Realistic base prices per Bali sub-region slug (USD/night)
BASE_PRICES = {
    "canggu":   {"villa": (120, 280), "apartment": (55, 110)},
    "ubud":     {"villa": (90, 200),  "apartment": (40, 80)},
    "kuta":     {"villa": (70, 160),  "apartment": (30, 70)},
    "seminyak": {"villa": (150, 380), "apartment": (70, 130)},
    "nusa_dua": {"villa": (200, 500), "apartment": (90, 180)},
    "uluwatu":  {"villa": (130, 320), "apartment": (60, 120)},
}

PROPERTY_TYPES = ["villa", "apartment"]


class Command(BaseCommand):
    help = "Seed realistic price data for dev/testing (Bali sub-regions)"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--clear", action="store_true")
        parser.add_argument("--listings-per-day", type=int, default=20)

    def handle(self, *args, **options):
        from apps.geo.models import Country, Region
        from apps.sources.models import Source, ScrapeJob
        from apps.prices.models import PriceRecord, DailyAggregate
        from apps.prices.services import PriceAnalysisService

        try:
            indonesia = Country.objects.get(iso2="ID")
        except Country.DoesNotExist:
            raise CommandError(
                "Indonesia not found — run `manage.py seed_geo` and the Bali "
                "data migration first."
            )
        regions = {r.slug: r for r in Region.objects.filter(country=indonesia, parent__isnull=False)}
        if not regions:
            raise CommandError(
                "No Bali sub-regions found under Indonesia — run the Bali data migration first."
            )

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            PriceRecord.objects.all().delete()
            DailyAggregate.objects.all().delete()
            Source.objects.filter(country=indonesia).delete()

        # Ensure sources exist
        sources = self._ensure_sources(indonesia, regions)

        days = options["days"]
        listings_per_day = options["listings_per_day"]
        today = date.today()

        self.stdout.write(f"Seeding {days} days × {len(regions)} regions × {listings_per_day} listings...")

        records_total = 0
        with transaction.atomic():
            for delta in range(days, 0, -1):
                target_date = today - timedelta(days=delta)
                records = []

                for slug, region in regions.items():
                    source = sources.get(slug)
                    if not source:
                        continue
                    for i in range(listings_per_day):
                        prop = random.choice(PROPERTY_TYPES)
                        lo, hi = BASE_PRICES[slug][prop]

                        # Slight weekly seasonality: weekends +10%
                        multiplier = 1.10 if target_date.weekday() >= 5 else 1.0
                        # Slow upward trend over time
                        trend = 1 + (days - delta) * 0.001
                        price = round(random.uniform(lo, hi) * multiplier * trend, 2)

                        records.append(PriceRecord(
                            source=source,
                            country=indonesia,
                            region=region,
                            market_type="rental",
                            listing_id=f"{slug}_{prop}_{i:03d}",
                            title=f"Beautiful {prop.title()} in {region.name} #{i+1}",
                            price_usd=price,
                            bedrooms=random.randint(1, 4),
                            bathrooms=random.randint(1, 3),
                            guests_capacity=random.randint(2, 8),
                            rating=round(random.uniform(4.0, 5.0), 1),
                            reviews_count=random.randint(5, 300),
                            property_type=prop,
                            listing_url=f"https://example.com/{slug}/{prop}/{i}",
                            scraped_at=target_date,
                        ))

                PriceRecord.objects.bulk_create(records, ignore_conflicts=True)
                records_total += len(records)

                # Compute aggregates for this day
                PriceAnalysisService.compute_daily_aggregates(target_date)

        agg_count = DailyAggregate.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {records_total} price records → {agg_count} daily aggregates."
        ))

    def _ensure_sources(self, indonesia, regions: dict) -> dict:
        from apps.sources.models import Source

        source_defs = [
            ("airbnb_canggu",   "airbnb",  "canggu"),
            ("airbnb_ubud",     "airbnb",  "ubud"),
            ("airbnb_kuta",     "airbnb",  "kuta"),
            ("booking_canggu",  "booking", "canggu"),
            ("booking_seminyak","booking", "seminyak"),
            ("booking_nusa_dua","booking", "nusa_dua"),
            ("booking_uluwatu", "booking", "uluwatu"),
        ]
        sources = {}
        for name, src_type, slug in source_defs:
            region = regions.get(slug)
            if not region:
                continue
            obj, created = Source.objects.get_or_create(
                name=name,
                defaults={
                    "source_type": src_type,
                    "market_type": "rental",
                    "country": indonesia,
                    "region": region,
                    "is_active": True,
                },
            )
            sources[slug] = obj
            if created:
                self.stdout.write(f"  Created source: {name}")
        return sources
