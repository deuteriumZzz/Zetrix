from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def scrape_source_task(self, source_pk: str) -> dict:
    from .models import Source
    from .services import ScrapingService

    try:
        source = Source.objects.get(pk=source_pk, is_active=True)
        service = ScrapingService(source)
        job = service.run()
        return {"job_pk": str(job.pk), "status": job.status, "records": job.records_fetched}
    except Source.DoesNotExist:
        return {"error": f"Source {source_pk} not found or inactive"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)
