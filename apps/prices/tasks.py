from celery import shared_task
import logging
from datetime import date

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def compute_aggregates_task(self, target_date_str: str | None = None) -> dict:
    from apps.prices.services import PriceAnalysisService

    target = (
        date.fromisoformat(target_date_str)
        if target_date_str
        else date.today()
    )
    try:
        PriceAnalysisService.compute_daily_aggregates(target)
        return {"status": "success", "date": str(target)}
    except Exception as exc:
        logger.exception(f"compute_aggregates_task failed for {target}")
        raise self.retry(exc=exc, countdown=120)
