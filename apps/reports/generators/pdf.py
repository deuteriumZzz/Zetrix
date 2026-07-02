from __future__ import annotations
import io
import logging
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from django.core.files.base import ContentFile

from .base import AbstractReportGenerator
from apps.prices.models import DailyAggregate

logger = logging.getLogger(__name__)

_PADDING_STYLE = [
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
]


class PDFReportGenerator(AbstractReportGenerator):

    def generate(self) -> Path:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
        styles = getSampleStyleSheet()
        elements = self._build_elements(styles)

        doc.build(elements)
        buffer.seek(0)

        filename = self._filename("pdf")
        self.report.file.save(filename, ContentFile(buffer.read()), save=True)
        logger.info(f"PDF report generated: {filename}")
        return Path(self.report.file.path)

    def _build_elements(self, styles) -> list:
        elements = []
        title_style = ParagraphStyle(
            "Title", parent=styles["Heading1"], fontSize=20, spaceAfter=12
        )
        elements.append(Paragraph(self.report.title, title_style))
        elements.append(Spacer(1, 0.5 * cm))

        place = self.report.region.name if self.report.region else (
            self.report.country.name if self.report.country else "All"
        )
        meta = [
            ["Region", place],
            ["Market type", self.report.market_type or "All"],
            ["Period", f"{self.report.date_from} -> {self.report.date_to}"],
            ["Generated", str(date.today())],
        ]
        meta_table = Table(meta, colWidths=[4 * cm, 12 * cm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F0F4F8")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ] + _PADDING_STYLE))
        elements.append(meta_table)
        elements.append(Spacer(1, 1 * cm))

        # Chart
        chart_image = self._build_chart()
        if chart_image:
            elements.append(Image(chart_image, width=16 * cm, height=8 * cm))
            elements.append(Spacer(1, 1 * cm))

        # Data table — conditional filter to avoid empty result set
        qs = DailyAggregate.objects.filter(
            date__range=(self.report.date_from, self.report.date_to),
        )
        if self.report.country:
            qs = qs.filter(country=self.report.country)
        if self.report.region:
            qs = qs.filter(region=self.report.region)
        if self.report.market_type:
            qs = qs.filter(market_type=self.report.market_type)
        aggregates = qs.order_by("date")[:30]

        if aggregates:
            elements.append(Paragraph("Daily Price Summary", styles["Heading2"]))
            elements.append(Spacer(1, 0.3 * cm))
            table_data = [["Date", "Avg Price", "Min", "Max", "Listings", "Change %"]]
            for agg in aggregates:
                table_data.append([
                    str(agg.date),
                    f"${agg.avg_price_usd}",
                    f"${agg.min_price_usd}",
                    f"${agg.max_price_usd}",
                    str(agg.listings_count),
                    f"{agg.price_change_pct or 0:+.1f}%",
                ])
            data_table = Table(table_data, colWidths=[3 * cm] * 6)
            data_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C5F8A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ] + _PADDING_STYLE))
            elements.append(data_table)

        return elements

    def _build_chart(self) -> io.BytesIO | None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates

            qs = DailyAggregate.objects.filter(
                date__range=(self.report.date_from, self.report.date_to),
            )
            if self.report.country:
                qs = qs.filter(country=self.report.country)
            if self.report.region:
                qs = qs.filter(region=self.report.region)
            aggregates = list(qs.order_by("date").values("date", "avg_price_usd"))

            if not aggregates:
                return None

            dates = [a["date"] for a in aggregates]
            prices = [float(a["avg_price_usd"]) for a in aggregates]

            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(dates, prices, color="#2C5F8A", linewidth=2, marker="o", markersize=4)
            ax.fill_between(dates, prices, alpha=0.15, color="#2C5F8A")
            chart_place = self.report.region.name if self.report.region else (
                self.report.country.name if self.report.country else "All"
            )
            ax.set_title(f"Average Daily Price - {chart_place}", fontsize=13)
            ax.set_ylabel("USD / night")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            plt.xticks(rotation=45)
            ax.grid(True, alpha=0.3)
            fig.tight_layout()

            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return buf
        except Exception as exc:
            logger.warning(f"Chart generation failed: {exc}")
            return None
