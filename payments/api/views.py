import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.security_alerts import record_threshold_alert
from common.views.base import AuthenticatedAsyncAPIView
from payments.serializers import (
    CheckoutSessionCreateSerializer,
    PaymentStatusSerializer,
)
from payments.services.stripe_service import (
    InvalidWebhookError,
    PaymentProcessingError,
    StripeService,
)
from payments.throttling import PaymentCheckoutThrottle, PaymentStatusThrottle


logger = logging.getLogger(__name__)
webhook_security_logger = logging.getLogger("security.webhook")


def _extract_client_ip(request):
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


@extend_schema(
    request=CheckoutSessionCreateSerializer,
    responses={201: EnvelopeSuccess, 400: EnvelopeError, 401: EnvelopeError},
)
class OneTimeCheckoutSessionView(AuthenticatedAsyncAPIView):
    throttle_classes = [PaymentCheckoutThrottle]

    async def post(self, request):
        serializer = CheckoutSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = await sync_to_async(StripeService.create_one_time_checkout_session)(
                request.user,
                **serializer.validated_data,
            )
            return self.success(payload, status=status.HTTP_201_CREATED)
        except PaymentProcessingError as exc:
            logger.warning("One-time checkout creation failed for user=%s", request.user.id)
            return self.error(exc.message, status=exc.status_code)


@extend_schema(
    request=CheckoutSessionCreateSerializer,
    responses={201: EnvelopeSuccess, 400: EnvelopeError, 401: EnvelopeError},
)
class RecurringCheckoutSessionView(AuthenticatedAsyncAPIView):
    throttle_classes = [PaymentCheckoutThrottle]

    async def post(self, request):
        serializer = CheckoutSessionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = await sync_to_async(StripeService.create_recurring_checkout_session)(
                request.user,
                **serializer.validated_data,
            )
            return self.success(payload, status=status.HTTP_201_CREATED)
        except PaymentProcessingError as exc:
            logger.warning("Recurring checkout creation failed for user=%s", request.user.id)
            return self.error(exc.message, status=exc.status_code)


@extend_schema(
    request=PaymentStatusSerializer,
    responses={200: EnvelopeSuccess, 400: EnvelopeError, 401: EnvelopeError},
)
class CheckoutSessionStatusView(AuthenticatedAsyncAPIView):
    throttle_classes = [PaymentStatusThrottle]

    async def post(self, request):
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = await sync_to_async(
                StripeService.get_checkout_session_status_for_user
            )(
                request.user,
                serializer.validated_data["session_id"],
            )
            return self.success(payload)
        except PaymentProcessingError as exc:
            return self.error(exc.message, status=exc.status_code)


@extend_schema(exclude=True)
@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request):
        client_ip = _extract_client_ip(request)
        if settings.STRIPE_WEBHOOK_IP_ALLOWLIST:
            if client_ip not in settings.STRIPE_WEBHOOK_IP_ALLOWLIST:
                webhook_security_logger.warning(
                    "Blocked Stripe webhook request from disallowed ip=%s path=%s",
                    client_ip,
                    request.path,
                )
                count, crossed_now = record_threshold_alert(
                    event_type="webhook_block",
                    identifier=client_ip or "unknown",
                    threshold=settings.SECURITY_WEBHOOK_BLOCK_ALERT_THRESHOLD,
                    window_seconds=settings.SECURITY_ALERT_WINDOW_SECONDS,
                )
                if crossed_now:
                    webhook_security_logger.error(
                        "Webhook block spike detected count=%s window_s=%s ip=%s path=%s",
                        count,
                        settings.SECURITY_ALERT_WINDOW_SECONDS,
                        client_ip,
                        request.path,
                    )
                return JsonResponse({"detail": "Forbidden"}, status=403)

        sig_header = request.headers.get("Stripe-Signature", "")

        try:
            event = StripeService.construct_webhook_event(request.body, sig_header)
            StripeService.handle_event(event)
            return HttpResponse(status=200)
        except InvalidWebhookError as exc:
            logger.warning("Invalid Stripe webhook received: %s", exc)
            return JsonResponse({"detail": str(exc)}, status=400)
        except Exception:
            logger.exception("Unhandled Stripe webhook failure")
            return JsonResponse({"detail": "Webhook processing failed."}, status=500)
