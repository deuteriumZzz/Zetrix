from rest_framework.routers import DefaultRouter
from .views import PriceRecordViewSet, DailyAggregateViewSet

router = DefaultRouter()
router.register("records", PriceRecordViewSet, basename="price-record")
router.register("aggregates", DailyAggregateViewSet, basename="daily-aggregate")

urlpatterns = router.urls
