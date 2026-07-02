from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_report_task(
    self, report_pk: str, notify_chat_id: str | None = None
) -> dict:
    from .models import Report, ReportFormat
    from .generators.pdf import PDFReportGenerator
    from .generators.csv_export import CSVReportGenerator
    from django.utils import timezone

    claimed = Report.objects.filter(pk=report_pk, status="pending").update(
        status="generating"
    )
    if not claimed:
        logger.warning(f"Report {report_pk} already claimed or not found, skipping.")
        return {"status": "skipped", "report_pk": report_pk}

    try:
        report = Report.objects.get(pk=report_pk)

        if report.format == ReportFormat.PDF:
            generator = PDFReportGenerator(report)
        else:
            generator = CSVReportGenerator(report)

        generator.generate()

        report.status = "ready"
        report.generated_at = timezone.now()
        report.save(update_fields=["status", "generated_at"])

        if notify_chat_id:
            send_report_telegram_task.delay(report_pk, chat_id=notify_chat_id)

        return {"status": "success", "report_pk": report_pk}

    except Report.DoesNotExist:
        logger.error(f"Report {report_pk} not found after claim")
        return {"status": "error", "detail": "not found"}
    except Exception as exc:
        Report.objects.filter(pk=report_pk).update(
            status="failed", error_message=str(exc)
        )
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_report_telegram_task(
    self, report_pk: str, chat_id: str | None = None
) -> None:
    from .models import Report
    from apps.notifications.senders.telegram import TelegramSender

    try:
        report = Report.objects.get(pk=report_pk)
    except Report.DoesNotExist:
        logger.error(f"send_report_telegram_task: Report {report_pk} not found")
        return

    try:
        sender = TelegramSender(chat_id=chat_id)
        sender.send_report(report)
    except Exception as exc:
        logger.error(f"Telegram send failed for report {report_pk}: {exc}")
        raise self.retry(exc=exc, countdown=30)
