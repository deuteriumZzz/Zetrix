from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from .models import AlertRule, NotificationLog, Subscription
from .serializers import AlertRuleSerializer, NotificationLogSerializer, SubscriptionSerializer


class AlertRuleViewSet(viewsets.ModelViewSet):
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["country", "region", "market_type", "is_active"]
    search_fields = ["name"]


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationLog.objects.select_related("alert_rule").all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["channel", "is_success"]
    ordering_fields = ["sent_at"]


class SubscriptionViewSet(viewsets.ModelViewSet):
    """Authenticated users manage their own subscriptions."""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["country", "region", "market_type", "is_active"]

    def get_queryset(self):
        return Subscription.objects.filter(user=self.request.user).select_related("country", "region")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
