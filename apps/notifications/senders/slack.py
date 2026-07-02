from __future__ import annotations
import logging
import httpx
from .base import AbstractNotificationSender

logger = logging.getLogger(__name__)


class SlackSender(AbstractNotificationSender):
    """Sends messages to a Slack webhook."""

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def send_text(self, message: str) -> bool:
        try:
            resp = httpx.post(
                self._webhook_url,
                json={"text": message},
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error(f"SlackSender.send_text failed: {exc}")
            return False

    def send_report(self, report) -> bool:
        message = (
            f":bar_chart: *{report.title}*\n"
            f"Region: {report.region or 'All'} | Market: {report.market_type or 'All'}\n"
            f"Period: {report.date_from} → {report.date_to}\n"
            f"Status: {report.status}"
        )
        return self.send_text(message)
