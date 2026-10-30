from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Report
from .serializers import ReportSerializer, ReportCreateSerializer
from .services import ReportService


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related("requested_by").all()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "format", "country", "region", "market_type"]
    ordering_fields = ["created_at", "generated_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return ReportCreateSerializer
        return ReportSerializer

    def perform_create(self, serializer):
        report = serializer.save(requested_by=self.request.user)
        ReportService.generate_async(str(report.pk))

    @action(detail=True, methods=["post"], url_path="send-telegram")
    def send_telegram(self, request, pk=None):
        report = self.get_object()
        if report.status != "ready":
            return Response(
                {"detail": "Report is not ready yet."}, status=status.HTTP_400_BAD_REQUEST
            )
        ReportService.send_to_telegram(str(report.pk))
        return Response({"detail": "Sending to Telegram."}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["post"], url_path="retry")
    def retry(self, request, pk=None):
        report = self.get_object()
        if report.status not in ("pending", "failed"):
            return Response(
                {"detail": "Only pending or failed reports can be retried."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Report.objects.filter(pk=report.pk).update(status="pending", error_message="")
        ReportService.generate_async(str(report.pk))
        return Response({"detail": "Regeneration queued."}, status=status.HTTP_202_ACCEPTED)
