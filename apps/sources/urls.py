from rest_framework.routers import DefaultRouter
from .views import SourceViewSet, ScrapeJobViewSet

router = DefaultRouter()
router.register("", SourceViewSet, basename="source")
router.register("jobs", ScrapeJobViewSet, basename="scrape-job")

urlpatterns = router.urls
