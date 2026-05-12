from rest_framework import serializers
from django.conf import settings
from urllib.parse import urlparse


class CheckoutSessionCreateSerializer(serializers.Serializer):
    price_lookup_key = serializers.CharField(max_length=100)
    return_url = serializers.URLField(max_length=1000)

    def validate_return_url(self, value: str) -> str:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        scheme = (parsed.scheme or "").lower()
        allowed_hosts = {
            (allowed or "").strip().lower().lstrip(".")
            for allowed in getattr(settings, "PAYMENT_RETURN_URL_ALLOWED_HOSTS", [])
            if allowed
        }

        if settings.IS_PRODUCTION and scheme != "https":
            raise serializers.ValidationError("return_url must use HTTPS in production.")

        if allowed_hosts:
            if host in allowed_hosts:
                return value

            if any(host.endswith(f".{allowed}") for allowed in allowed_hosts):
                return value

            raise serializers.ValidationError("return_url host is not allowed.")

        return value


class PaymentStatusSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
