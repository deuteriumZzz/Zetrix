from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.db import IntegrityError
from django.test import override_settings
from django.urls import reverse

from apps.notifications.models import NotificationLog
from apps.notifications.senders.telegram import TelegramSender
from apps.notifications.tasks import check_subscriptions_task
from tests.factories import (
    DailyAggregateFactory,
    RegionFactory,
    SubscriptionFactory,
    UserFactory,
    UserProfileFactory,
)

pytestmark = pytest.mark.django_db


class TestSubscriptionModel:
    def test_unique_together_user_region_market_type(self):
        user = UserFactory()
        region = RegionFactory(slug="canggu", name="Canggu")
        SubscriptionFactory(user=user, country=region.country, region=region, market_type="rental")
        with pytest.raises(IntegrityError):
            SubscriptionFactory(
                user=user, country=region.country, region=region, market_type="rental"
            )

    def test_str(self):
        user = UserFactory(username="alice")
        region = RegionFactory(slug="canggu", name="Canggu")
        sub = SubscriptionFactory(
            user=user, country=region.country, region=region,
            market_type="rental", threshold_pct="5.00",
        )
        assert str(sub) == "alice -> Canggu/rental (>5.00%)"


class TestCheckSubscriptionsTask:
    def test_skips_when_no_aggregate_for_today(self):
        SubscriptionFactory(market_type="rental", direction="any", threshold_pct="5")
        result = check_subscriptions_task()
        assert result == {"sent": 0, "skipped": 1, "date": str(date.today())}

    def test_skips_when_aggregate_has_no_price_change_pct(self):
        region = RegionFactory(slug="canggu", name="Canggu")
        SubscriptionFactory(country=region.country, region=region, market_type="rental", threshold_pct="5")
        DailyAggregateFactory(
            date=date.today(), country=region.country, region=region,
            market_type="rental", price_change_pct=None,
        )
        result = check_subscriptions_task()
        assert result["sent"] == 0
        assert result["skipped"] == 1

    def test_skips_when_user_has_no_telegram_chat_id(self):
        user = UserFactory()
        UserProfileFactory(user=user, telegram_chat_id=None)
        region = RegionFactory(slug="canggu", name="Canggu")
        SubscriptionFactory(
            user=user, country=region.country, region=region,
            market_type="rental", threshold_pct="5", direction="any",
        )
        DailyAggregateFactory(
            date=date.today(), country=region.country, region=region,
            market_type="rental", price_change_pct="10.00",
        )
        result = check_subscriptions_task()
        assert result["sent"] == 0
        assert result["skipped"] == 1
        assert NotificationLog.objects.count() == 0

    def test_triggers_and_logs_on_exact_threshold_boundary(self):
        user = UserFactory()
        UserProfileFactory(user=user, telegram_chat_id="12345")
        region = RegionFactory(slug="canggu", name="Canggu")
        SubscriptionFactory(
            user=user, country=region.country, region=region,
            market_type="rental", threshold_pct="5.00", direction="up",
        )
        DailyAggregateFactory(
            date=date.today(), country=region.country, region=region, market_type="rental",
            price_change_pct="5.00", avg_price_usd="150.00",
        )
        with patch(
            "apps.notifications.senders.telegram.TelegramSender.send_price_alert",
            return_value=True,
        ) as mock_send:
            result = check_subscriptions_task()

        assert result["sent"] == 1
        assert result["skipped"] == 0
        mock_send.assert_called_once()
        log = NotificationLog.objects.get()
        assert log.is_success is True
        assert log.channel == "telegram"

    def test_down_direction_only_triggers_on_negative_change(self):
        user = UserFactory()
        UserProfileFactory(user=user, telegram_chat_id="12345")
        region = RegionFactory(slug="ubud", name="Ubud")
        SubscriptionFactory(
            user=user, country=region.country, region=region,
            market_type="rental", threshold_pct="5.00", direction="down",
        )
        DailyAggregateFactory(
            date=date.today(), country=region.country, region=region, market_type="rental",
            price_change_pct="5.00", avg_price_usd="150.00",  # positive change, direction=down
        )
        result = check_subscriptions_task()
        assert result["sent"] == 0
        assert result["skipped"] == 1

    def test_logs_failed_send_but_still_records_notification_log(self):
        user = UserFactory()
        UserProfileFactory(user=user, telegram_chat_id="12345")
        region = RegionFactory(slug="canggu", name="Canggu")
        SubscriptionFactory(
            user=user, country=region.country, region=region,
            market_type="rental", threshold_pct="5.00", direction="any",
        )
        DailyAggregateFactory(
            date=date.today(), country=region.country, region=region, market_type="rental",
            price_change_pct="10.00", avg_price_usd="150.00",
        )
        with patch(
            "apps.notifications.senders.telegram.TelegramSender.send_price_alert",
            return_value=False,
        ):
            result = check_subscriptions_task()

        assert result["sent"] == 0
        assert result["skipped"] == 1
        log = NotificationLog.objects.get()
        assert log.is_success is False
        assert log.error == "Send failed"


class TestAlertRuleViewSetPermissions:
    def test_regular_authenticated_user_forbidden(self, auth_client):
        resp = auth_client.get(reverse("api_v1:alert-rule-list"))
        assert resp.status_code == 403

    def test_admin_allowed(self, admin_client):
        resp = admin_client.get(reverse("api_v1:alert-rule-list"))
        assert resp.status_code == 200


class TestNotificationLogViewSetPermissions:
    def test_regular_authenticated_user_forbidden(self, auth_client):
        resp = auth_client.get(reverse("api_v1:notification-log-list"))
        assert resp.status_code == 403


class TestSubscriptionViewSet:
    def test_user_only_sees_own_subscriptions(self, auth_client, user, other_user):
        canggu = RegionFactory(slug="canggu", name="Canggu")
        ubud = RegionFactory(country=canggu.country, slug="ubud", name="Ubud")
        SubscriptionFactory(user=user, country=canggu.country, region=canggu, market_type="rental")
        SubscriptionFactory(user=other_user, country=ubud.country, region=ubud, market_type="rental")
        resp = auth_client.get(reverse("api_v1:subscription-list"))
        assert resp.status_code == 200
        assert resp.data["count"] == 1

    def test_user_cannot_retrieve_other_users_subscription(self, auth_client, other_user):
        region = RegionFactory(slug="ubud", name="Ubud")
        other_sub = SubscriptionFactory(
            user=other_user, country=region.country, region=region, market_type="rental"
        )
        resp = auth_client.get(reverse("api_v1:subscription-detail", args=[other_sub.pk]))
        assert resp.status_code == 404

    def test_create_forces_requesting_user(self, auth_client, user):
        region = RegionFactory(slug="canggu", name="Canggu")
        resp = auth_client.post(reverse("api_v1:subscription-list"), {
            "country": str(region.country.id), "region": str(region.id),
            "market_type": "rental", "threshold_pct": "5.00", "direction": "any",
        })
        assert resp.status_code == 201
        assert resp.data["username"] == user.username


class TestTelegramSender:
    @override_settings(TELEGRAM_BOT_TOKEN="", TELEGRAM_CHAT_ID="")
    def test_send_text_returns_false_without_crashing_when_not_configured(self):
        assert TelegramSender().send_text("hello") is False

    @override_settings(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_CHAT_ID="123")
    def test_send_text_posts_and_returns_true_on_success(self):
        mock_resp = MagicMock(raise_for_status=MagicMock())
        with patch("apps.notifications.senders.telegram.httpx.post", return_value=mock_resp) as mock_post:
            assert TelegramSender().send_text("hello") is True
        assert mock_post.call_args.kwargs["json"]["text"] == "hello"

    @override_settings(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_CHAT_ID="123")
    def test_send_text_returns_false_on_http_error(self):
        with patch("apps.notifications.senders.telegram.httpx.post", side_effect=RuntimeError("boom")):
            assert TelegramSender().send_text("hello") is False

    @override_settings(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_CHAT_ID="123")
    def test_send_price_alert_formats_message_and_delegates_to_send_text(self):
        with patch.object(TelegramSender, "send_text", return_value=True) as mock_send_text:
            TelegramSender().send_price_alert(
                region="canggu", market_type="rental", change_pct=12.5, avg_price=150.0,
                threshold_pct=5.0,
            )
        message = mock_send_text.call_args.args[0]
        assert "Canggu" in message
        assert "+12.5%" in message
        assert "📈" in message
