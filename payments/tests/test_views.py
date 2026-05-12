from datetime import date
from unittest.mock import patch

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase


User = get_user_model()


class PaymentViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pay@example.com",
            firstname="Pay",
            lastname="User",
            password="Password123!",
            dob=date(2000, 1, 1),
            bio="bio",
        )
        login_response = self.client.post(
            "/authorized/login/",
            {
                "email": "pay@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        self.access_token = login_response.data["access"]

    def test_one_time_checkout_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(
            "/payments/one-time/checkout/",
            {
                "price_lookup_key": "single_drop",
                "return_url": "https://example.com/return",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    @patch("payments.api.views.StripeService.create_one_time_checkout_session")
    def test_one_time_checkout_returns_session_payload(self, create_checkout):
        create_checkout.return_value = {
            "client_secret": "secret",
            "session_id": "cs_123",
            "payment_kind": "one_time",
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            "/payments/one-time/checkout/",
            {
                "price_lookup_key": "single_drop",
                "return_url": "https://example.com/return",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["session_id"], "cs_123")

    @patch("payments.api.views.StripeService.create_recurring_checkout_session")
    def test_recurring_checkout_returns_session_payload(self, create_checkout):
        create_checkout.return_value = {
            "client_secret": "secret",
            "session_id": "cs_recurring",
            "payment_kind": "recurring",
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            "/payments/recurring/checkout/",
            {
                "price_lookup_key": "vip_30_day",
                "return_url": "https://example.com/return",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["payment_kind"], "recurring")

    @patch("payments.api.views.StripeService.get_checkout_session_status_for_user")
    def test_checkout_status_is_authenticated(self, get_status):
        get_status.return_value = {
            "session_id": "cs_123",
            "status": "open",
            "checkout_url": "",
            "completed_at": None,
            "expires_at": None,
            "metadata": {"payment_kind": "one_time"},
        }

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")
        response = self.client.post(
            "/payments/checkout/status/",
            {"session_id": "cs_123"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["status"], "open")

    @override_settings(STRIPE_WEBHOOK_IP_ALLOWLIST=["127.0.0.1"])
    @patch("payments.api.views.StripeService.construct_webhook_event")
    def test_webhook_rejects_disallowed_ip(self, construct_webhook_event):
        response = self.client.post(
            "/payments/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            REMOTE_ADDR="203.0.113.10",
        )
        self.assertEqual(response.status_code, 403)
        construct_webhook_event.assert_not_called()

    @override_settings(STRIPE_WEBHOOK_IP_ALLOWLIST=["127.0.0.1"])
    @patch("payments.api.views.StripeService.handle_event")
    @patch("payments.api.views.StripeService.construct_webhook_event")
    def test_webhook_accepts_allowed_ip(self, construct_webhook_event, handle_event):
        construct_webhook_event.return_value = {"id": "evt_test", "type": "checkout.session.completed", "data": {"object": {}}}
        response = self.client.post(
            "/payments/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            REMOTE_ADDR="127.0.0.1",
            HTTP_STRIPE_SIGNATURE="t=1,v1=test",
        )
        self.assertEqual(response.status_code, 200)
        construct_webhook_event.assert_called_once()
        handle_event.assert_called_once()

    @override_settings(
        STRIPE_WEBHOOK_IP_ALLOWLIST=["127.0.0.1"],
        SECURITY_WEBHOOK_BLOCK_ALERT_THRESHOLD=1,
        SECURITY_ALERT_WINDOW_SECONDS=300,
    )
    @patch("payments.api.views.webhook_security_logger.error")
    def test_webhook_block_spike_logs_error(self, mock_error):
        cache.clear()
        response = self.client.post(
            "/payments/webhooks/stripe/",
            data="{}",
            content_type="application/json",
            REMOTE_ADDR="203.0.113.10",
        )
        self.assertEqual(response.status_code, 403)
        mock_error.assert_called_once()

