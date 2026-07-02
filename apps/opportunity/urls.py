from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BusinessClimateReviewViewSet, CountryBusinessClimateView

router = DefaultRouter()
router.register("reviews", BusinessClimateReviewViewSet, basename="business-climate-review")

urlpatterns = [
    path("countries/<str:iso2>/", CountryBusinessClimateView.as_view(), name="country-business-climate"),
] + router.urls
