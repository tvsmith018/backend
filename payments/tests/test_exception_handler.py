from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import Throttled
from rest_framework.test import APIRequestFactory

from common.exceptions import api_exception_handler


class DummyView:
    pass


class ApiExceptionHandlerTests(SimpleTestCase):
    def test_logs_rate_limit_telemetry_on_throttled_exception(self):
        factory = APIRequestFactory()
        request = factory.post("/payments/one-time/checkout/", {})
        request.META["REMOTE_ADDR"] = "203.0.113.10"
        request.user = type("User", (), {"is_authenticated": True, "pk": 42})()

        exc = Throttled(wait=60)
        context = {"request": request, "view": DummyView()}

        with patch("common.exceptions.security_logger.warning") as mock_warning:
            response = api_exception_handler(exc, context)

        self.assertEqual(response.status_code, 429)
        mock_warning.assert_called_once()

    @override_settings(
        SECURITY_THROTTLE_ALERT_THRESHOLD=1,
        SECURITY_ALERT_WINDOW_SECONDS=300,
    )
    def test_logs_error_when_throttle_spike_threshold_crossed(self):
        cache.clear()
        factory = APIRequestFactory()
        request = factory.post("/payments/one-time/checkout/", {})
        request.META["REMOTE_ADDR"] = "203.0.113.10"
        request.user = type("User", (), {"is_authenticated": True, "pk": 42})()
        exc = Throttled(wait=60)
        context = {"request": request, "view": DummyView()}

        with (
            patch("common.exceptions.security_logger.warning"),
            patch("common.exceptions.security_logger.error") as mock_error,
        ):
            response = api_exception_handler(exc, context)

        self.assertEqual(response.status_code, 429)
        mock_error.assert_called_once()
