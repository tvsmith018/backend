import logging
from datetime import UTC
from datetime import timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from payments.models import (
    BillingCustomer,
    BillingProduct,
    BillingPrice,
    Subscription,
    CheckoutSession,
    PaymentRecord,
    PaymentMethod,
    WebhookEvent,
)


stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)
CardError = stripe.error.CardError
InvalidRequestError = stripe.error.InvalidRequestError
SignatureVerificationError = stripe.error.SignatureVerificationError
StripeError = stripe.error.StripeError


class PaymentProcessingError(Exception):
    def __init__(self, message, *, code=None, status_code=400, retryable=False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.retryable = retryable


class InvalidWebhookError(Exception):
    pass


class StripeService:
    REALTIME_GROUP_PREFIX = "billing_user_"
    RECURRING_CYCLE_DAYS = 30
    OPEN_SUBSCRIPTION_STATUSES = (
        Subscription.Status.INCOMPLETE,
        Subscription.Status.ACTIVE,
        Subscription.Status.PAST_DUE,
    )

    @staticmethod
    def _stripe_value(obj, key, default=None):
        if obj is None:
            return default

        try:
            return obj[key]
        except (KeyError, TypeError):
            return getattr(obj, key, default)

    @staticmethod
    def _plain_stripe_data(value):
        if hasattr(value, "to_dict_recursive"):
            return StripeService._plain_stripe_data(value.to_dict_recursive())

        if hasattr(value, "to_dict"):
            return StripeService._plain_stripe_data(value.to_dict())

        if isinstance(value, dict):
            return {
                key: StripeService._plain_stripe_data(item)
                for key, item in value.items()
            }

        if isinstance(value, (list, tuple)):
            return [StripeService._plain_stripe_data(item) for item in value]

        if hasattr(value, "items"):
            return {
                key: StripeService._plain_stripe_data(item)
                for key, item in value.items()
            }

        return value

    @staticmethod
    def _dt_from_timestamp(ts):
        if not ts:
            return None
        return timezone.datetime.fromtimestamp(ts, tz=UTC)

    @staticmethod
    def _next_period_end(start_at):
        return start_at + timedelta(days=StripeService.RECURRING_CYCLE_DAYS)

    @staticmethod
    def _get_billing_timezone():
        return ZoneInfo(settings.BILLING_TIME_ZONE)

    @staticmethod
    def _format_for_billing_timezone(value):
        if not value:
            return None
        return timezone.localtime(value, StripeService._get_billing_timezone()).isoformat()

    @staticmethod
    def _publish_payment_event(user_id, payload):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        async_to_sync(channel_layer.group_send)(
            f"{StripeService.REALTIME_GROUP_PREFIX}{user_id}",
            {
                "type": "payment.event",
                "payload": payload,
            },
        )

    @staticmethod
    def _get_dunning_attempt_count(subscription):
        metadata = subscription.metadata or {}
        return int(metadata.get("dunning_attempt_count", 0) or 0)

    @staticmethod
    def _set_dunning_state(subscription, *, attempt_count=None, next_retry_at=None, last_error=None):
        metadata = dict(subscription.metadata or {})
        if attempt_count is not None:
            metadata["dunning_attempt_count"] = attempt_count
        if next_retry_at is not None:
            metadata["next_retry_at"] = next_retry_at.isoformat() if next_retry_at else None
        if last_error is not None:
            metadata["last_dunning_error"] = last_error
        subscription.metadata = metadata

    @staticmethod
    def _disable_subscription_plan(subscription, *, error, attempt_count):
        subscription.status = Subscription.Status.UNPAID
        subscription.cancel_at_period_end = True
        subscription.canceled_at = timezone.now()
        subscription.plan_disabled = True
        subscription.plan_disabled_reason = "max_payment_failures"
        subscription.plan_disabled_attempt_count = attempt_count
        subscription.plan_disabled_at = subscription.canceled_at
        metadata = dict(subscription.metadata or {})
        metadata["plan_disabled"] = True
        metadata["plan_disabled_reason"] = "max_payment_failures"
        metadata["plan_disabled_attempt_count"] = attempt_count
        metadata["plan_disabled_at"] = subscription.canceled_at.isoformat()
        metadata["next_retry_at"] = None
        metadata["last_dunning_error"] = {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
        }
        subscription.metadata = metadata

    @staticmethod
    def _get_next_retry_at(subscription):
        metadata = subscription.metadata or {}
        next_retry_raw = metadata.get("next_retry_at")
        if not next_retry_raw:
            return None
        try:
            return timezone.datetime.fromisoformat(next_retry_raw)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _serialize_checkout_session(checkout_session):
        return {
            "session_id": checkout_session.provider_checkout_session_id,
            "status": checkout_session.status,
            "checkout_url": checkout_session.checkout_url,
            "completed_at": checkout_session.completed_at.isoformat()
            if checkout_session.completed_at
            else None,
            "expires_at": checkout_session.expires_at.isoformat()
            if checkout_session.expires_at
            else None,
            "metadata": checkout_session.metadata,
        }

    @staticmethod
    def _queue_receipt_email(payment_record):
        from payments.tasks import send_payment_receipt

        send_payment_receipt.delay(payment_record.id)

    @staticmethod
    def _queue_failed_payment_email(payment_record):
        from payments.tasks import send_failed_payment_email

        send_failed_payment_email.delay(payment_record.id)

    @staticmethod
    def _mark_existing_payment_methods_not_default(customer):
        PaymentMethod.objects.filter(customer=customer, is_default=True).update(
            is_default=False
        )

    @staticmethod
    def _assert_customer_can_start_subscription(customer):
        existing_subscription = (
            Subscription.objects.filter(
                customer=customer,
                status__in=StripeService.OPEN_SUBSCRIPTION_STATUSES,
            )
            .order_by("-updated_at")
            .first()
        )
        if existing_subscription:
            raise PaymentProcessingError(
                "You already have a subscription in progress or active. Only one subscription can be held at a time.",
                code="subscription_already_exists",
                status_code=409,
            )

    @staticmethod
    def _normalize_stripe_error(exc):
        code = getattr(exc, "code", None)
        user_message = "Payment processing failed. Please try again."
        retryable = False
        status_code = 400

        if isinstance(exc, CardError):
            user_message = {
                "insufficient_funds": "Card declined due to insufficient funds.",
                "expired_card": "Card has expired.",
                "incorrect_cvc": "Card security code is incorrect.",
                "invalid_cvc": "Card security code is invalid.",
                "incorrect_number": "Card number is incorrect.",
                "invalid_number": "Card number is invalid.",
                "processing_error": "Card processor returned an error. Please retry.",
                "card_declined": "Card was declined.",
            }.get(code, exc.user_message or user_message)
        elif isinstance(exc, InvalidRequestError):
            user_message = "Payment request was invalid. Please verify the billing setup."
        elif isinstance(exc, StripeError):
            user_message = "Payment provider is temporarily unavailable. Please retry."
            retryable = True
            status_code = 502

        return PaymentProcessingError(
            user_message,
            code=code or exc.__class__.__name__,
            status_code=status_code,
            retryable=retryable,
        )

    @staticmethod
    def _build_checkout_metadata(user, price_lookup_key, payment_kind):
        return {
            "user_id": str(user.pk),
            "price_lookup_key": price_lookup_key,
            "payment_kind": payment_kind,
        }

    @staticmethod
    def get_or_create_customer(user):
        billing_customer = BillingCustomer.objects.filter(user=user).first()
        if billing_customer:
            return billing_customer

        stripe_customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.firstname} {user.lastname}".strip(),
            metadata={
                "user_id": str(user.pk),
                "app": "bigchiefent",
            },
        )

        return BillingCustomer.objects.create(
            user=user,
            provider=BillingCustomer.Provider.STRIPE,
            provider_customer_id=stripe_customer["id"],
            email=StripeService._stripe_value(stripe_customer, "email") or user.email,
            metadata=StripeService._plain_stripe_data(
                StripeService._stripe_value(stripe_customer, "metadata", {}) or {}
            ),
        )

    @staticmethod
    def sync_product_and_price_by_lookup_key(lookup_key: str):
        prices = stripe.Price.list(
            lookup_keys=[lookup_key],
            expand=["data.product"],
            limit=1,
        ).data

        if not prices:
            raise PaymentProcessingError(
                f"No Stripe price found for lookup key '{lookup_key}'.",
                status_code=404,
            )

        stripe_price = prices[0]
        stripe_product = stripe_price["product"]
        recurring = StripeService._plain_stripe_data(
            StripeService._stripe_value(stripe_price, "recurring", {}) or {}
        )

        product, _ = BillingProduct.objects.update_or_create(
            provider_product_id=stripe_product["id"],
            defaults={
                "name": StripeService._stripe_value(stripe_product, "name", ""),
                "code": (
                    StripeService._plain_stripe_data(
                        StripeService._stripe_value(stripe_product, "metadata", {}) or {}
                    )
                ).get(
                    "plan_name",
                    StripeService._stripe_value(stripe_product, "name", "").lower().replace(" ", "-"),
                )[:100],
                "product_type": BillingProduct.ProductType.SUBSCRIPTION
                if StripeService._stripe_value(stripe_price, "type") == "recurring"
                else BillingProduct.ProductType.ONE_TIME,
                "description": StripeService._stripe_value(stripe_product, "description") or "",
                "active": StripeService._stripe_value(stripe_product, "active", True),
                "metadata": StripeService._plain_stripe_data(
                    StripeService._stripe_value(stripe_product, "metadata", {}) or {}
                ),
            },
        )

        price, _ = BillingPrice.objects.update_or_create(
            provider_price_id=stripe_price["id"],
            defaults={
                "product": product,
                "lookup_key": lookup_key,
                "price_type": BillingPrice.PriceType.RECURRING
                if StripeService._stripe_value(stripe_price, "type") == "recurring"
                else BillingPrice.PriceType.ONE_TIME,
                "unit_amount": StripeService._stripe_value(stripe_price, "unit_amount") or 0,
                "currency": StripeService._stripe_value(stripe_price, "currency", "usd"),
                "recurring_interval": recurring.get("interval"),
                "interval_count": recurring.get("interval_count", 1),
                "active": StripeService._stripe_value(stripe_price, "active", True),
                "metadata": StripeService._plain_stripe_data(
                    StripeService._stripe_value(stripe_price, "metadata", {}) or {}
                ),
            },
        )

        return product, price

    @staticmethod
    @transaction.atomic
    def create_checkout_session(user, price_lookup_key: str, return_url: str, *, payment_kind: str):
        billing_customer = StripeService.get_or_create_customer(user)
        if payment_kind == "recurring":
            StripeService._assert_customer_can_start_subscription(billing_customer)
        _, local_price = StripeService.sync_product_and_price_by_lookup_key(price_lookup_key)
        metadata = StripeService._build_checkout_metadata(user, price_lookup_key, payment_kind)

        if payment_kind == "one_time":
            if local_price.price_type != BillingPrice.PriceType.ONE_TIME:
                raise PaymentProcessingError(
                    "This price is not configured for a one-time payment."
                )
        elif payment_kind == "recurring":
            if local_price.price_type != BillingPrice.PriceType.RECURRING:
                raise PaymentProcessingError(
                    "This price is not configured for recurring billing."
                )
        else:
            raise PaymentProcessingError("Unsupported payment type.")

        try:
            stripe_session = stripe.checkout.Session.create(
                ui_mode="embedded",
                mode="payment",
                customer=billing_customer.provider_customer_id,
                line_items=[
                    {
                        "price": local_price.provider_price_id,
                        "quantity": 1,
                    }
                ],
                return_url=return_url,
                metadata=metadata,
                payment_intent_data={
                    "metadata": metadata,
                    **(
                        {"setup_future_usage": "off_session"}
                        if payment_kind == "recurring"
                        else {}
                    ),
                },
            )
        except StripeError as exc:
            raise StripeService._normalize_stripe_error(exc) from exc

        CheckoutSession.objects.update_or_create(
            provider_checkout_session_id=stripe_session["id"],
            defaults={
                "customer": billing_customer,
                "price": local_price,
                "status": StripeService._stripe_value(stripe_session, "status", CheckoutSession.Status.OPEN),
                "checkout_url": StripeService._stripe_value(stripe_session, "url", "") or "",
                "success_url": return_url,
                "cancel_url": "",
                "expires_at": StripeService._dt_from_timestamp(
                    StripeService._stripe_value(stripe_session, "expires_at")
                ),
                "metadata": {
                    **StripeService._plain_stripe_data(
                        StripeService._stripe_value(stripe_session, "metadata", {}) or {}
                    ),
                    "payment_kind": payment_kind,
                },
            },
        )

        StripeService._publish_payment_event(
            user.pk,
            {
                "type": "payment.checkout.created",
                "session_id": stripe_session["id"],
                "payment_kind": payment_kind,
                "status": StripeService._stripe_value(stripe_session, "status", CheckoutSession.Status.OPEN),
            },
        )

        return {
            "client_secret": stripe_session["client_secret"],
            "session_id": stripe_session["id"],
            "payment_kind": payment_kind,
        }

    @staticmethod
    def create_one_time_checkout_session(user, price_lookup_key: str, return_url: str):
        return StripeService.create_checkout_session(
            user,
            price_lookup_key,
            return_url,
            payment_kind="one_time",
        )

    @staticmethod
    def create_recurring_checkout_session(user, price_lookup_key: str, return_url: str):
        return StripeService.create_checkout_session(
            user,
            price_lookup_key,
            return_url,
            payment_kind="recurring",
        )

    @staticmethod
    def retrieve_checkout_session(session_id: str):
        return stripe.checkout.Session.retrieve(
            session_id,
            expand=["payment_intent.payment_method", "customer"],
        )

    @staticmethod
    def get_checkout_session_status_for_user(user, session_id):
        checkout_session = CheckoutSession.objects.filter(
            provider_checkout_session_id=session_id,
            customer__user=user,
        ).first()
        if not checkout_session:
            raise PaymentProcessingError("Checkout session not found.", status_code=404)

        return StripeService._serialize_checkout_session(checkout_session)

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str):
        try:
            return stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=settings.STRIPE_WEBHOOK_SECRET,
                tolerance=settings.STRIPE_WEBHOOK_TOLERANCE_SECONDS,
            )
        except (ValueError, SignatureVerificationError) as exc:
            raise InvalidWebhookError(str(exc)) from exc

    @staticmethod
    @transaction.atomic
    def handle_event(event):
        webhook_event, created = WebhookEvent.objects.get_or_create(
            provider_event_id=event["id"],
            defaults={
                "event_type": event["type"],
                "processed": False,
                "payload": event,
            },
        )

        if not created and webhook_event.processed:
            logger.info("Skipping already processed webhook event=%s", event["id"])
            return webhook_event

        event_type = event["type"]
        data_object = event["data"]["object"]

        if event_type == "checkout.session.completed":
            StripeService._handle_checkout_session_completed(data_object)
        elif event_type == "checkout.session.expired":
            StripeService._handle_checkout_session_expired(data_object)
        elif event_type == "payment_intent.payment_failed":
            StripeService._handle_payment_intent_failed(data_object)
        else:
            logger.info("Received unsupported Stripe event=%s", event_type)

        webhook_event.event_type = event_type
        webhook_event.payload = event
        webhook_event.processed = True
        webhook_event.save(update_fields=["event_type", "payload", "processed", "updated_at"])

        return webhook_event

    @staticmethod
    def _sync_payment_method(customer, payment_method_id):
        pm = stripe.PaymentMethod.retrieve(payment_method_id)
        card = StripeService._plain_stripe_data(
            StripeService._stripe_value(pm, "card", {}) or {}
        )
        StripeService._mark_existing_payment_methods_not_default(customer)
        payment_method, _ = PaymentMethod.objects.update_or_create(
            provider_payment_method_id=pm["id"],
            defaults={
                "customer": customer,
                "brand": card.get("brand", ""),
                "last4": card.get("last4", ""),
                "exp_month": card.get("exp_month"),
                "exp_year": card.get("exp_year"),
                "is_default": True,
                "active": True,
                "metadata": StripeService._plain_stripe_data(
                    StripeService._stripe_value(pm, "metadata", {}) or {}
                ),
            },
        )
        return payment_method

    @staticmethod
    def _record_one_time_payment(checkout, session):
        payment_intent_id = session.get("payment_intent")
        payment_record, _ = PaymentRecord.objects.update_or_create(
            provider_payment_intent_id=payment_intent_id,
            defaults={
                "customer": checkout.customer,
                "subscription": None,
                "amount": session.get("amount_total") or checkout.price.unit_amount,
                "currency": session.get("currency", checkout.price.currency),
                "status": PaymentRecord.Status.SUCCEEDED,
                "paid_at": timezone.now(),
                "metadata": {
                    **(session.get("metadata", {}) or {}),
                    "payment_kind": "one_time",
                    "checkout_session_id": checkout.provider_checkout_session_id,
                },
            },
        )
        StripeService._queue_receipt_email(payment_record)

    @staticmethod
    def _activate_recurring_subscription_from_session(checkout, session):
        payment_intent_id = session.get("payment_intent")
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        payment_method_id = StripeService._stripe_value(payment_intent, "payment_method")
        if not payment_method_id:
            raise PaymentProcessingError(
                "No payment method was attached for recurring billing."
            )

        StripeService._sync_payment_method(checkout.customer, payment_method_id)
        cycle_start = timezone.now()
        cycle_end = StripeService._next_period_end(cycle_start)

        subscription, _ = Subscription.objects.update_or_create(
            provider_subscription_id=f"manual_{checkout.provider_checkout_session_id}",
            defaults={
                "customer": checkout.customer,
                "product": checkout.price.product,
                "price": checkout.price,
                "status": Subscription.Status.ACTIVE,
                "current_period_start": cycle_start,
                "current_period_end": cycle_end,
                "cancel_at_period_end": False,
                "canceled_at": None,
                "started_at": cycle_start,
                "metadata": {
                    **(session.get("metadata", {}) or {}),
                    "billing_engine": "celery_manual_recurring",
                    "payment_method_id": payment_method_id,
                },
            },
        )

        payment_record, _ = PaymentRecord.objects.update_or_create(
            provider_payment_intent_id=payment_intent_id,
            defaults={
                "customer": checkout.customer,
                "subscription": subscription,
                "amount": session.get("amount_total") or checkout.price.unit_amount,
                "currency": session.get("currency", checkout.price.currency),
                "status": PaymentRecord.Status.SUCCEEDED,
                "paid_at": timezone.now(),
                "metadata": {
                    **(session.get("metadata", {}) or {}),
                    "payment_kind": "recurring_initial",
                    "checkout_session_id": checkout.provider_checkout_session_id,
                },
            },
        )
        StripeService._queue_receipt_email(payment_record)

    @staticmethod
    def _handle_checkout_session_completed(session):
        checkout = CheckoutSession.objects.filter(
            provider_checkout_session_id=session["id"]
        ).select_related("customer", "customer__user", "price", "price__product").first()
        if not checkout:
            return

        checkout.status = CheckoutSession.Status.COMPLETE
        checkout.completed_at = timezone.now()
        checkout.metadata = session.get("metadata", {}) or {}
        checkout.save(update_fields=["status", "completed_at", "metadata", "updated_at"])

        payment_kind = checkout.metadata.get("payment_kind")
        if payment_kind == "recurring":
            StripeService._activate_recurring_subscription_from_session(checkout, session)
        else:
            StripeService._record_one_time_payment(checkout, session)

        StripeService._publish_payment_event(
            checkout.customer.user_id,
            {
                "type": f"payment.{payment_kind}.completed",
                "session_id": checkout.provider_checkout_session_id,
                "status": checkout.status,
                "payment_intent_id": session.get("payment_intent"),
            },
        )

    @staticmethod
    def _handle_checkout_session_expired(session):
        checkout = CheckoutSession.objects.filter(
            provider_checkout_session_id=session["id"]
        ).select_related("customer").first()
        if not checkout:
            return

        checkout.status = CheckoutSession.Status.EXPIRED
        checkout.metadata = session.get("metadata", {}) or {}
        checkout.save(update_fields=["status", "metadata", "updated_at"])

        StripeService._publish_payment_event(
            checkout.customer.user_id,
            {
                "type": "payment.checkout.expired",
                "session_id": checkout.provider_checkout_session_id,
                "payment_kind": checkout.metadata.get("payment_kind"),
            },
        )

    @staticmethod
    def _handle_payment_intent_failed(payment_intent):
        metadata = StripeService._plain_stripe_data(
            payment_intent.get("metadata", {}) or {}
        )
        user_id = metadata.get("user_id")
        billing_customer = BillingCustomer.objects.filter(
            provider_customer_id=payment_intent.get("customer")
        ).first()
        subscription = None
        subscription_id = metadata.get("subscription_id")
        if subscription_id:
            subscription = Subscription.objects.filter(pk=subscription_id).first()
            if subscription:
                subscription.status = Subscription.Status.PAST_DUE
                subscription.save(update_fields=["status", "updated_at"])

        payment_record, _ = PaymentRecord.objects.update_or_create(
            provider_payment_intent_id=payment_intent["id"],
            defaults={
                "customer": billing_customer,
                "subscription": subscription,
                "amount": payment_intent.get("amount", 0),
                "currency": payment_intent.get("currency", "usd"),
                "status": PaymentRecord.Status.FAILED,
                "paid_at": None,
                "metadata": {
                    **metadata,
                    "last_payment_error": StripeService._plain_stripe_data(
                        payment_intent.get("last_payment_error") or {}
                    ),
                },
            },
        )
        StripeService._queue_failed_payment_email(payment_record)

        if user_id:
            StripeService._publish_payment_event(
                int(user_id),
                {
                    "type": "payment.failed",
                    "payment_intent_id": payment_intent["id"],
                    "error": StripeService._plain_stripe_data(
                        payment_intent.get("last_payment_error") or {}
                    ),
                },
            )

    @staticmethod
    def _build_failed_payment_metadata(error, *, payment_kind, subscription=None):
        metadata = {
            "payment_kind": payment_kind,
            "error_code": error.code,
            "error_message": error.message,
            "retryable": error.retryable,
        }
        if subscription:
            metadata["subscription_id"] = subscription.id
        return metadata

    @staticmethod
    def _record_failed_subscription_charge(subscription, error):
        attempt_count = StripeService._get_dunning_attempt_count(subscription) + 1
        next_retry_at = timezone.now() + timedelta(days=settings.BILLING_DUNNING_RETRY_DAYS)
        payment_record = PaymentRecord.objects.create(
            customer=subscription.customer,
            subscription=subscription,
            provider_payment_intent_id=f"failed_{subscription.id}_{uuid4().hex}",
            amount=subscription.price.unit_amount,
            currency=subscription.price.currency,
            status=PaymentRecord.Status.FAILED,
            paid_at=None,
            metadata=StripeService._build_failed_payment_metadata(
                error,
                payment_kind="recurring_cycle",
                subscription=subscription,
            ),
        )
        StripeService._queue_failed_payment_email(payment_record)
        if attempt_count >= settings.BILLING_DUNNING_MAX_FAILURES:
            StripeService._disable_subscription_plan(
                subscription,
                error=error,
                attempt_count=attempt_count,
            )
            StripeService._set_dunning_state(
                subscription,
                attempt_count=attempt_count,
                next_retry_at=None,
            )
        else:
            subscription.status = Subscription.Status.PAST_DUE
            StripeService._set_dunning_state(
                subscription,
                attempt_count=attempt_count,
                next_retry_at=next_retry_at,
                last_error={
                    "code": error.code,
                    "message": error.message,
                    "retryable": error.retryable,
                },
            )
        subscription.save(
            update_fields=[
                "status",
                "cancel_at_period_end",
                "canceled_at",
                "plan_disabled",
                "plan_disabled_reason",
                "plan_disabled_attempt_count",
                "plan_disabled_at",
                "metadata",
                "updated_at",
            ]
        )
        logger.warning(
            "Recurring charge failed for subscription=%s attempt=%s status=%s code=%s",
            subscription.id,
            attempt_count,
            subscription.status,
            error.code,
        )
        StripeService._publish_payment_event(
            subscription.customer.user_id,
            {
                "type": "payment.recurring.failed",
                "subscription_id": subscription.id,
                "error_code": error.code,
                "message": error.message,
                "retryable": error.retryable,
                "attempt_count": attempt_count,
                "next_retry_at": next_retry_at.isoformat(),
                "next_retry_at_local": StripeService._format_for_billing_timezone(next_retry_at),
            },
        )

    @staticmethod
    @transaction.atomic
    def collect_subscription_payment(subscription):
        logger.info(
            "Attempting recurring charge for subscription=%s customer=%s due_at=%s",
            subscription.id,
            subscription.customer_id,
            subscription.current_period_end,
        )
        payment_method = (
            PaymentMethod.objects.filter(customer=subscription.customer, is_default=True, active=True)
            .order_by("-updated_at")
            .first()
        )
        if not payment_method:
            raise PaymentProcessingError(
                "No default payment method is available for this subscription.",
                code="missing_payment_method",
                status_code=400,
            )

        due_at = subscription.current_period_end or StripeService._next_period_end(
            subscription.started_at
        )

        try:
            idempotency_key = (
                f"subscription-charge:{subscription.id}:{due_at.astimezone(UTC).isoformat()}"
            )
            payment_intent = stripe.PaymentIntent.create(
                amount=subscription.price.unit_amount,
                currency=subscription.price.currency,
                customer=subscription.customer.provider_customer_id,
                payment_method=payment_method.provider_payment_method_id,
                off_session=True,
                confirm=True,
                metadata={
                    "user_id": str(subscription.customer.user_id),
                    "subscription_id": str(subscription.id),
                    "payment_kind": "recurring_cycle",
                    "price_lookup_key": subscription.price.lookup_key,
                },
                idempotency_key=idempotency_key,
            )
        except StripeError as exc:
            raise StripeService._normalize_stripe_error(exc) from exc

        next_end = StripeService._next_period_end(due_at)
        subscription.current_period_start = due_at
        subscription.current_period_end = next_end
        subscription.status = Subscription.Status.ACTIVE
        subscription.cancel_at_period_end = False
        subscription.canceled_at = None
        subscription.plan_disabled = False
        subscription.plan_disabled_reason = ""
        subscription.plan_disabled_attempt_count = 0
        subscription.plan_disabled_at = None
        subscription.metadata = {
            **(subscription.metadata or {}),
            "last_successful_payment_intent_id": payment_intent["id"],
            "next_retry_at": None,
            "last_dunning_error": None,
            "dunning_attempt_count": 0,
        }
        subscription.save(
            update_fields=[
                "current_period_start",
                "current_period_end",
                "status",
                "cancel_at_period_end",
                "canceled_at",
                "plan_disabled",
                "plan_disabled_reason",
                "plan_disabled_attempt_count",
                "plan_disabled_at",
                "metadata",
                "updated_at",
            ]
        )

        payment_record, _ = PaymentRecord.objects.update_or_create(
            provider_payment_intent_id=payment_intent["id"],
            defaults={
                "customer": subscription.customer,
                "subscription": subscription,
                "amount": StripeService._stripe_value(
                    payment_intent,
                    "amount",
                    subscription.price.unit_amount,
                ),
                "currency": StripeService._stripe_value(
                    payment_intent,
                    "currency",
                    subscription.price.currency,
                ),
                "status": PaymentRecord.Status.SUCCEEDED,
                "paid_at": timezone.now(),
                "metadata": {
                    "payment_kind": "recurring_cycle",
                    "subscription_id": subscription.id,
                    "due_at": due_at.isoformat(),
                },
            },
        )
        StripeService._queue_receipt_email(payment_record)
        logger.info(
            "Recurring charge succeeded for subscription=%s payment_intent=%s next_due_at=%s",
            subscription.id,
            payment_intent["id"],
            next_end,
        )

        StripeService._publish_payment_event(
            subscription.customer.user_id,
            {
                "type": "payment.recurring.succeeded",
                "subscription_id": subscription.id,
                "payment_intent_id": payment_intent["id"],
                "next_due_at": next_end.isoformat(),
                "next_due_at_local": StripeService._format_for_billing_timezone(next_end),
            },
        )

        return payment_intent

    @staticmethod
    def collect_due_recurring_payments():
        due_subscriptions = (
            Subscription.objects.select_related("customer", "customer__user", "price")
            .filter(
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.PAST_DUE],
                current_period_end__isnull=False,
                current_period_end__lte=timezone.now(),
                cancel_at_period_end=False,
            )
        )
        processed = 0
        succeeded = 0
        failed = 0

        for subscription in due_subscriptions:
            next_retry_at = StripeService._get_next_retry_at(subscription)
            if next_retry_at and next_retry_at > timezone.now():
                logger.info(
                    "Skipping subscription=%s until next_retry_at=%s",
                    subscription.id,
                    next_retry_at,
                )
                continue
            processed += 1
            try:
                StripeService.collect_subscription_payment(subscription)
                succeeded += 1
            except PaymentProcessingError as exc:
                failed += 1
                StripeService._record_failed_subscription_charge(subscription, exc)
                if exc.retryable:
                    raise

        logger.info(
            "Recurring billing sweep complete processed=%s succeeded=%s failed=%s timezone=%s",
            processed,
            succeeded,
            failed,
            settings.BILLING_TIME_ZONE,
        )
        return {
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
        }
