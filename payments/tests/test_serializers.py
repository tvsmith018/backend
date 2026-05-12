from django.test import SimpleTestCase, override_settings

from payments.serializers import CheckoutSessionCreateSerializer


class CheckoutSessionCreateSerializerTests(SimpleTestCase):
    @override_settings(
        IS_PRODUCTION=False,
        PAYMENT_RETURN_URL_ALLOWED_HOSTS=["example.com", "www.bigchiefnewz.com"],
    )
    def test_accepts_allowed_return_url(self):
        serializer = CheckoutSessionCreateSerializer(
            data={
                "price_lookup_key": "single_drop",
                "return_url": "https://www.bigchiefnewz.com/account/billing",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @override_settings(
        IS_PRODUCTION=False,
        PAYMENT_RETURN_URL_ALLOWED_HOSTS=["example.com"],
    )
    def test_rejects_disallowed_return_url_host(self):
        serializer = CheckoutSessionCreateSerializer(
            data={
                "price_lookup_key": "single_drop",
                "return_url": "https://evil.example.net/steal",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("return_url", serializer.errors)

    @override_settings(
        IS_PRODUCTION=True,
        PAYMENT_RETURN_URL_ALLOWED_HOSTS=["example.com"],
    )
    def test_rejects_non_https_in_production(self):
        insecure_return_url = "http" + "://example.com/return"
        serializer = CheckoutSessionCreateSerializer(
            data={
                "price_lookup_key": "single_drop",
                "return_url": insecure_return_url,
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("return_url", serializer.errors)
