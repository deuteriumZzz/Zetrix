from django.core.management.base import BaseCommand
from apps.billing.models import Plan


class Command(BaseCommand):
    help = "Seeds the default Free/Pro plans. Safe to re-run (update_or_create)."

    def handle(self, *args, **options):
        Plan.objects.update_or_create(
            slug="free",
            defaults=dict(
                name="Free",
                price_usd_monthly=0,
                max_active_alerts=1,
                max_reports_per_month=1,
                business_climate_access=False,
                is_default=True,
                stripe_price_id="",
            ),
        )
        Plan.objects.update_or_create(
            slug="pro",
            defaults=dict(
                name="Pro",
                price_usd_monthly=9,
                max_active_alerts=0,
                max_reports_per_month=0,
                business_climate_access=True,
                is_default=False,
                stripe_price_id="",  # set to a real Stripe Price ID (price_...) before enabling checkout
            ),
        )
        self.stdout.write(self.style.SUCCESS("Seeded Free and Pro plans."))
