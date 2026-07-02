from rest_framework.routers import DefaultRouter
from .views import AlertRuleViewSet, NotificationLogViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register("alerts", AlertRuleViewSet, basename="alert-rule")
router.register("logs", NotificationLogViewSet, basename="notification-log")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = router.urls
