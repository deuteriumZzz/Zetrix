from django.urls import path
from .views import CreateCheckoutSessionView, MyPlanView, PlanListView, StripeWebhookView

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="plan-list"),
    path("me/", MyPlanView.as_view(), name="my-plan"),
    path("checkout/", CreateCheckoutSessionView.as_view(), name="billing-checkout"),
    path("webhook/", StripeWebhookView.as_view(), name="stripe-webhook"),
]
