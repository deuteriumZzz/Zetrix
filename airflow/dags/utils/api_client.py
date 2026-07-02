from __future__ import annotations
import os, logging, httpx

logger = logging.getLogger(__name__)
DJANGO_API_URL = os.getenv("DJANGO_API_URL", "http://web:8000/api/v1")
DJANGO_API_TOKEN = os.getenv("DJANGO_API_TOKEN", "dev-token")


class DjangoAPIClient:
    def __init__(self):
        self._c = httpx.Client(
            base_url=DJANGO_API_URL,
            headers={"Authorization": f"Token {DJANGO_API_TOKEN}"},
            timeout=30,
        )

    def trigger_scrape(self, source_id):
        r = self._c.post(f"/sources/{source_id}/trigger/"); r.raise_for_status(); return r.json()

    def trigger_report(self, payload):
        r = self._c.post("/reports/", json=payload); r.raise_for_status(); return r.json()

    def send_report_telegram(self, report_pk):
        r = self._c.post(f"/reports/{report_pk}/send-telegram/"); r.raise_for_status(); return r.json()

    def get_sources(self):
        sources = []
        url = "/sources/?is_active=true"
        while url:
            r = self._c.get(url); r.raise_for_status(); data = r.json()
            sources.extend(data.get("results", []))
            next_url = data.get("next")
            url = next_url.replace(str(self._c.base_url), "", 1) if next_url else None
        return sources

    def __del__(self):
        self._c.close()
