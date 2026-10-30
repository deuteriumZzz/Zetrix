from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination


class LargePageNumberPagination(PageNumberPagination):
    """Allows callers to opt into a bigger page via ?page_size=, capped at 500."""

    page_size_query_param = "page_size"
    max_page_size = 500


class TriggerActionMixin:
    """Adds a /trigger/ action to any ViewSet to run async tasks."""

    trigger_task = None  # override in subclass: e.g. tasks.scrape_source

    @action(detail=True, methods=["post"], url_path="trigger")
    def trigger(self, request, pk=None):
        obj = self.get_object()
        if self.trigger_task is None:
            return Response(
                {"detail": "No task configured."}, status=status.HTTP_501_NOT_IMPLEMENTED
            )
        task = self.trigger_task.delay(str(obj.pk))
        return Response({"task_id": task.id, "status": "queued"}, status=status.HTTP_202_ACCEPTED)
