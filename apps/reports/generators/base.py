from __future__ import annotations
import abc
from pathlib import Path
from django.conf import settings


class AbstractReportGenerator(abc.ABC):
    """All report format generators implement this interface."""

    def __init__(self, report) -> None:
        self.report = report
        self.output_dir = Path(settings.REPORTS_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    def generate(self) -> Path:
        """Generate the report file and attach it to self.report.file."""
        ...

    def _filename(self, ext: str) -> str:
        return f"report_{self.report.pk}.{ext}"
