from __future__ import annotations
import abc


class AbstractNotificationSender(abc.ABC):
    """All notification channels implement this interface."""

    @abc.abstractmethod
    def send_text(self, message: str) -> bool:
        ...

    @abc.abstractmethod
    def send_report(self, report) -> bool:
        ...
