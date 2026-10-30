from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Plan, UserSubscription
from .serializers import PlanSerializer, UserSubscriptionSerializer
from .services import get_plan_for_user


class PlanListView(generics.ListAPIView):
    """Public pricing page data."""
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class MyPlanView(APIView):
    """Current user's plan — falls back to the default free plan if no active subscription."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan = get_plan_for_user(request.user)
        sub = UserSubscription.objects.filter(user=request.user).select_related("plan").first()
        return Response({
            "plan": PlanSerializer(plan).data,
            "subscription": UserSubscriptionSerializer(sub).data if sub else None,
        })


class CreateCheckoutSessionView(APIView):
    """Starts a Stripe Checkout session for the given plan. Requires
    STRIPE_SECRET_KEY to be configured — returns 501 otherwise (dev/demo mode)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Payments are not configured on this deployment yet."},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        plan_id = request.data.get("plan_id")
        try:
            plan = Plan.objects.get(pk=plan_id)
        except (Plan.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Unknown plan."}, status=status.HTTP_400_BAD_REQUEST)
        if not plan.stripe_price_id:
            return Response({"detail": "This plan has no Stripe price configured."}, status=status.HTTP_400_BAD_REQUEST)

        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        sub, _ = UserSubscription.objects.get_or_create(
            user=request.user, defaults={"plan": plan}
        )
        if not sub.stripe_customer_id:
            customer = stripe.Customer.create(email=request.user.email or None, metadata={"user_id": str(request.user.pk)})
            sub.stripe_customer_id = customer.id
            sub.save(update_fields=["stripe_customer_id"])

        session = stripe.checkout.Session.create(
            customer=sub.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/pricing?checkout=success",
            cancel_url=f"{settings.FRONTEND_URL}/pricing?checkout=canceled",
            metadata={"user_id": str(request.user.pk), "plan_id": str(plan.pk)},
        )
        return Response({"checkout_url": session.url})


class StripeWebhookView(APIView):
    """Receives Stripe events and syncs UserSubscription status. Verifies the
    signature with STRIPE_WEBHOOK_SECRET — configure both before going live."""
    permission_classes = [AllowAny]

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return Response({"detail": "Webhook not configured."}, status=status.HTTP_501_NOT_IMPLEMENTED)

        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except (ValueError, stripe.error.SignatureVerificationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        obj = event["data"]["object"]
        event_type = event["type"]

        if event_type in ("customer.subscription.updated", "customer.subscription.created"):
            sub = UserSubscription.objects.filter(stripe_customer_id=obj["customer"]).first()
            if sub:
                sub.stripe_subscription_id = obj["id"]
                sub.status = "active" if obj["status"] == "active" else obj["status"]
                sub.save(update_fields=["stripe_subscription_id", "status"])
        elif event_type == "customer.subscription.deleted":
            sub = UserSubscription.objects.filter(stripe_customer_id=obj["customer"]).first()
            if sub:
                sub.status = "canceled"
                sub.save(update_fields=["status"])

        return Response({"received": True})
