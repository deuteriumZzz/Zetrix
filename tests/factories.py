import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.geo.models import Continent, Country
from apps.geo.models import Region as GeoRegion
from apps.notifications.models import AlertRule, Subscription
from apps.prices.models import DailyAggregate, PriceRecord
from apps.reports.models import Report
from apps.sources.models import MarketType, ScrapeJob, Source, SourceType
from apps.users.models import UserProfile


class ContinentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Continent
        django_get_or_create = ("code",)

    code = "AS"
    name = "Asia"
    slug = "asia"


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("iso2",)

    iso2 = "ID"
    iso3 = "IDN"
    name = "Indonesia"
    continent = factory.SubFactory(ContinentFactory)
    centroid_lat = -5.0
    centroid_lng = 120.0
    currency_code = "IDR"
    is_housing_supported = True


class RegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GeoRegion
        django_get_or_create = ("country", "slug")

    country = factory.SubFactory(CountryFactory)
    slug = "canggu"
    name = "Canggu"
    level = "city"
    parent = None
    centroid_lat = -8.6478
    centroid_lng = 115.1385


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "pass12345")
        if create:
            self.save()


class SourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Source

    name = factory.Sequence(lambda n: f"source-{n}")
    source_type = SourceType.AIRBNB
    market_type = MarketType.RENTAL
    country = factory.SubFactory(CountryFactory)
    region = factory.SubFactory(RegionFactory)
    is_active = True


class ScrapeJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScrapeJob

    source = factory.SubFactory(SourceFactory)
    status = "pending"


class PriceRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PriceRecord

    source = factory.SubFactory(SourceFactory)
    country = factory.SubFactory(CountryFactory)
    region = factory.SubFactory(RegionFactory)
    market_type = MarketType.RENTAL
    price_usd = "100.00"
    scraped_at = factory.LazyFunction(timezone.now)


class DailyAggregateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DailyAggregate

    date = factory.LazyFunction(lambda: timezone.now().date())
    country = factory.SubFactory(CountryFactory)
    region = factory.SubFactory(RegionFactory)
    market_type = MarketType.RENTAL
    property_type = "villa"
    avg_price_usd = "100.00"
    min_price_usd = "80.00"
    max_price_usd = "120.00"
    median_price_usd = "100.00"
    listings_count = 10


class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Report

    title = factory.Sequence(lambda n: f"Report {n}")
    date_from = factory.LazyFunction(lambda: timezone.now().date())
    date_to = factory.LazyFunction(lambda: timezone.now().date())


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    user = factory.SubFactory(UserFactory)
    country = factory.SubFactory(CountryFactory)
    region = factory.SubFactory(RegionFactory)
    market_type = "rental"
    threshold_pct = "5.00"
    direction = "any"


class AlertRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlertRule

    name = factory.Sequence(lambda n: f"alert-{n}")
    threshold_pct = "5.00"


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
