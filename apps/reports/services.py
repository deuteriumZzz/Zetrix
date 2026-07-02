from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


class ReportService:

    @staticmethod
    def generate_async(report_pk: str) -> None:
        from .tasks import generate_report_task
        generate_report_task.delay(report_pk)

    @staticmethod
    def send_to_telegram(report_pk: str) -> None:
        from .tasks import send_report_telegram_task
        send_report_telegram_task.delay(report_pk)
