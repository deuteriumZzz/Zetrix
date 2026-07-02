from __future__ import annotations
import logging
import httpx
from django.conf import settings
from .base import AbstractNotificationSender

logger = logging.getLogger(__name__)


class TelegramSender(AbstractNotificationSender):
    """Sends messages and PDF reports to a Telegram chat.

    Pass chat_id to override the default TELEGRAM_CHAT_ID (used for per-user notifications).
    """

    def __init__(self, chat_id: str | None = None) -> None:
        self._token = settings.TELEGRAM_BOT_TOKEN
        self._chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self._base_url = f"https://api.telegram.org/bot{self._token}"

    def send_text(self, message: str, parse_mode: str = "HTML") -> bool:
        if not self._token or not self._chat_id:
            logger.warning("Telegram not configured — skipping notification")
            return False

        try:
            resp = httpx.post(
                f"{self._base_url}/sendMessage",
                json={"chat_id": self._chat_id, "text": message, "parse_mode": parse_mode},
                timeout=10,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error(f"TelegramSender.send_text failed: {exc}")
            return False

    def send_report(self, report) -> bool:
        if not report.file:
            logger.warning(f"Report {report.pk} has no file to send")
            return False

        caption = (
            f"<b>{report.title}</b>\n"
            f"Region: {report.region or 'All'}\n"
            f"Market: {report.market_type or 'All'}\n"
            f"Period: {report.date_from} - {report.date_to}"
        )

        try:
            with report.file.open("rb") as f:
                resp = httpx.post(
                    f"{self._base_url}/sendDocument",
                    data={"chat_id": self._chat_id, "caption": caption, "parse_mode": "HTML"},
                    files={"document": (report.file.name, f, "application/pdf")},
                    timeout=30,
                )
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error(f"TelegramSender.send_report failed: {exc}")
            return False

    def send_price_alert(
        self,
        region: str,
        market_type: str,
        change_pct: float,
        avg_price: float,
        threshold_pct: float | None = None,
    ) -> bool:
        arrow = "up" if change_pct > 0 else "down"
        arrow_emoji = "📈" if change_pct > 0 else "📉"
        threshold_line = f"Threshold: {threshold_pct:+.1f}%\n" if threshold_pct else ""
        message = (
            f"{arrow_emoji} <b>Price Alert — {region.title()}</b>\n"
            f"Market: {market_type}\n"
            f"Change: <b>{change_pct:+.1f}%</b>\n"
            f"{threshold_line}"
            f"Avg price: <b>${avg_price:.0f}/night</b>"
        )
        return self.send_text(message)
