from rest_framework.routers import DefaultRouter

from .views import ContinentViewSet, CountryViewSet, RegionViewSet

router = DefaultRouter()
router.register("continents", ContinentViewSet, basename="continent")
router.register("countries", CountryViewSet, basename="country")
router.register("regions", RegionViewSet, basename="region")

urlpatterns = router.urls
