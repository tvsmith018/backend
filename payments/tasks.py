import logging

from celery import shared_task
import stripe

from common.services.email_service import EmailService
from common.services.idempotency import acquire_lock
from payments.models import PaymentRecord
from payments.services.stripe_service import PaymentProcessingError, StripeService


logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(
        stripe.error.APIConnectionError,
        stripe.error.APIError,
        stripe.error.RateLimitError,
    ),
    retry_backoff=60,
    retry_kwargs={"max_retries": 5},
)
def collect_due_recurring_payments(self):
    try:
        summary = StripeService.collect_due_recurring_payments()
        logger.info("Processed recurring billing sweep: %s", summary)
        return summary
    except PaymentProcessingError as exc:
        if exc.retryable:
            raise self.retry(exc=exc, countdown=60)
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 5})
def send_payment_receipt(self, payment_record_id):
    payment_record = (
        PaymentRecord.objects.select_related(
            "customer",
            "customer__user",
            "subscription",
            "subscription__product",
        )
        .get(pk=payment_record_id)
    )
    lock_key = f"payment-receipt:{payment_record_id}:{payment_record.status}"
    if not acquire_lock(lock_key, ttl=86400):
        return "Duplicate receipt ignored"

    amount_dollars = f"{payment_record.amount / 100:.2f}"
    payment_kind = (payment_record.metadata or {}).get("payment_kind", "payment")
    product_name = None
    if payment_record.subscription and payment_record.subscription.product:
        product_name = payment_record.subscription.product.name

    EmailService.send_html_email(
        subject="Big Chief Receipt",
        recipient_list=[payment_record.customer.user.email],
        template="emails/payments/receipt.html",
        context={
            "customer_name": (
                f"{payment_record.customer.user.firstname} "
                f"{payment_record.customer.user.lastname}"
            ).strip(),
            "amount": amount_dollars,
            "currency": payment_record.currency.upper(),
            "status": payment_record.status.replace("_", " ").title(),
            "paid_at": payment_record.paid_at,
            "payment_intent_id": payment_record.provider_payment_intent_id,
            "payment_kind": payment_kind.replace("_", " ").title(),
            "product_name": product_name,
            "subscription_id": payment_record.subscription_id,
        },
    )

    logger.info("Payment receipt sent for payment_record_id=%s", payment_record_id)
    return "Receipt sent"


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_kwargs={"max_retries": 5})
def send_failed_payment_email(self, payment_record_id):
    payment_record = (
        PaymentRecord.objects.select_related(
            "customer",
            "customer__user",
            "subscription",
            "subscription__product",
        )
        .get(pk=payment_record_id)
    )
    lock_key = f"payment-failure:{payment_record_id}:{payment_record.status}"
    if not acquire_lock(lock_key, ttl=86400):
        return "Duplicate failure email ignored"

    metadata = payment_record.metadata or {}
    product_name = None
    if payment_record.subscription and payment_record.subscription.product:
        product_name = payment_record.subscription.product.name

    EmailService.send_html_email(
        subject="Big Chief Payment Failed",
        recipient_list=[payment_record.customer.user.email],
        template="emails/payments/payment_failed.html",
        context={
            "customer_name": (
                f"{payment_record.customer.user.firstname} "
                f"{payment_record.customer.user.lastname}"
            ).strip(),
            "amount": f"{payment_record.amount / 100:.2f}",
            "currency": payment_record.currency.upper(),
            "payment_kind": metadata.get("payment_kind", "payment").replace("_", " ").title(),
            "product_name": product_name,
            "subscription_id": payment_record.subscription_id,
            "payment_reference": payment_record.provider_payment_intent_id,
            "error_code": metadata.get("error_code") or "payment_failed",
            "error_message": metadata.get("error_message")
            or (
                (metadata.get("last_payment_error") or {}).get("message")
                if isinstance(metadata.get("last_payment_error"), dict)
                else None
            )
            or "Your payment could not be processed.",
        },
    )

    logger.info("Payment failure email sent for payment_record_id=%s", payment_record_id)
    return "Failure email sent"
