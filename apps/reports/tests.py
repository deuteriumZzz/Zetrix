from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.reports.generators.csv_export import CSVReportGenerator
from apps.reports.models import Report
from tests.factories import PriceRecordFactory, RegionFactory, ReportFactory, SourceFactory

pytestmark = pytest.mark.django_db


class TestReportModel:
    def test_str(self):
        report = ReportFactory(title="Weekly Canggu", status="pending")
        assert str(report) == "Weekly Canggu [pending]"


class TestCSVReportGenerator:
    def test_generates_rows_for_a_specific_region(self, tmp_path):
        region = RegionFactory(slug="canggu", name="Canggu")
        source = SourceFactory(country=region.country, region=region, market_type="rental")
        scraped_at = timezone.make_aware(timezone.datetime(2026, 3, 1, 10, 0, 0))
        PriceRecordFactory(
            source=source, country=region.country, region=region, market_type="rental",
            price_usd="123.00", scraped_at=scraped_at,
        )
        report = ReportFactory(
            country=region.country, region=region, market_type="rental",
            date_from=date(2026, 3, 1), date_to=date(2026, 3, 1), format="csv",
        )
        with override_settings(REPORTS_DIR=tmp_path):
            CSVReportGenerator(report).generate()

        report.file.open("rb")
        content = report.file.read().decode("utf-8-sig")
        report.file.close()
        assert "123.00" in content

    def test_blank_region_means_all_regions(self, tmp_path):
        """
        Report.region/market_type are blank=True and mean "all regions/markets"
        (matching PDFReportGenerator's `if self.report.region: qs.filter(...)`
        pattern). Previously CSVReportGenerator filtered on a literal
        `region=""`, which can never match a real PriceRecord and silently
        produced an empty CSV — fixed to only filter when a value is set.
        """
        source = SourceFactory(market_type="rental")
        scraped_at = timezone.make_aware(timezone.datetime(2026, 3, 1, 10, 0, 0))
        PriceRecordFactory(
            source=source, country=source.country, region=source.region, market_type="rental",
            price_usd="123.00", scraped_at=scraped_at,
        )
        report = ReportFactory(
            market_type="",  # country/region left unset — "all regions / all markets"
            date_from=date(2026, 3, 1), date_to=date(2026, 3, 1), format="csv",
        )
        with override_settings(REPORTS_DIR=tmp_path):
            CSVReportGenerator(report).generate()

        report.file.open("rb")
        content = report.file.read().decode("utf-8-sig")
        report.file.close()
        assert "123.00" in content


class TestReportViewSet:
    def test_create_requires_auth(self, api_client):
        resp = api_client.post(reverse("api_v1:report-list"), {
            "title": "T", "date_from": "2026-01-01", "date_to": "2026-01-02", "format": "pdf",
        })
        assert resp.status_code == 401

    def test_create_sets_requested_by_and_queues_generation(self, auth_client, user):
        with patch("apps.reports.views.ReportService.generate_async") as mock_gen:
            resp = auth_client.post(reverse("api_v1:report-list"), {
                "title": "My Report", "date_from": "2026-01-01", "date_to": "2026-01-02",
                "format": "pdf",
            })
        assert resp.status_code == 201
        # create uses ReportCreateSerializer, which doesn't expose id/status —
        # only one report was created, so fetch it directly.
        report = Report.objects.get()
        assert report.requested_by_id == user.id
        mock_gen.assert_called_once_with(str(report.pk))

    def test_status_is_ignored_and_defaults_to_pending_on_create(self, auth_client):
        with patch("apps.reports.views.ReportService.generate_async"):
            resp = auth_client.post(reverse("api_v1:report-list"), {
                "title": "T", "date_from": "2026-01-01", "date_to": "2026-01-02",
                "format": "pdf", "status": "ready",
            })
        assert resp.status_code == 201
        report = Report.objects.get()
        assert report.status == "pending"

    def test_send_telegram_rejects_report_not_ready(self, auth_client):
        report = ReportFactory(status="pending")
        resp = auth_client.post(reverse("api_v1:report-send-telegram", args=[report.pk]))
        assert resp.status_code == 400

    def test_send_telegram_accepts_ready_report(self, auth_client):
        report = ReportFactory(status="ready")
        with patch("apps.reports.views.ReportService.send_to_telegram") as mock_send:
            resp = auth_client.post(reverse("api_v1:report-send-telegram", args=[report.pk]))
        assert resp.status_code == 202
        mock_send.assert_called_once_with(str(report.pk))
