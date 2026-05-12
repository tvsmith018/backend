from django.contrib import admin
from django.contrib import messages
from .models import (
    BillingCustomer,
    BillingProduct,
    BillingPrice,
    Subscription,
    PaymentMethod,
    CheckoutSession,
    PaymentRecord,
    WebhookEvent,
)
from payments.services.stripe_service import PaymentProcessingError, StripeService
from payments.tasks import send_failed_payment_email, send_payment_receipt


@admin.action(description="Retry recurring charge for selected subscriptions")
def retry_recurring_charge(modeladmin, request, queryset):
    attempted = 0
    successful = 0
    for subscription in queryset:
        attempted += 1
        try:
            StripeService.collect_subscription_payment(subscription)
            successful += 1
        except PaymentProcessingError as exc:
            modeladmin.message_user(
                request,
                f"Subscription {subscription.id} failed retry: {exc.message}",
                level=messages.WARNING,
            )
    if successful:
        modeladmin.message_user(
            request,
            f"Retried {successful} recurring charge(s) successfully out of {attempted}.",
            level=messages.SUCCESS,
        )


@admin.action(description="Queue success receipt email")
def resend_success_receipt(modeladmin, request, queryset):
    queued = 0
    for payment_record in queryset.filter(status=PaymentRecord.Status.SUCCEEDED):
        send_payment_receipt.delay(payment_record.id)
        queued += 1
    modeladmin.message_user(
        request,
        f"Queued {queued} success receipt email(s).",
        level=messages.SUCCESS,
    )


@admin.action(description="Queue failed payment email")
def resend_failure_email(modeladmin, request, queryset):
    queued = 0
    for payment_record in queryset.filter(status=PaymentRecord.Status.FAILED):
        send_failed_payment_email.delay(payment_record.id)
        queued += 1
    modeladmin.message_user(
        request,
        f"Queued {queued} failed payment email(s).",
        level=messages.SUCCESS,
    )


@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "provider",
        "provider_customer_id",
        "email",
        "is_active",
        "created_at",
    )
    search_fields = (
        "user__email",
        "email",
        "provider_customer_id",
    )
    list_filter = (
        "provider",
        "is_active",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(BillingProduct)
class BillingProductAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "code",
        "product_type",
        "provider_product_id",
        "active",
        "created_at",
    )
    search_fields = (
        "name",
        "code",
        "provider_product_id",
    )
    list_filter = (
        "product_type",
        "active",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(BillingPrice)
class BillingPriceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "product",
        "lookup_key",
        "provider_price_id",
        "price_type",
        "unit_amount",
        "currency",
        "recurring_interval",
        "active",
        "created_at",
    )
    search_fields = (
        "lookup_key",
        "provider_price_id",
        "product__name",
    )
    list_filter = (
        "price_type",
        "currency",
        "recurring_interval",
        "active",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "product",
        "price",
        "provider_subscription_id",
        "status",
        "plan_disabled",
        "cancel_at_period_end",
        "current_period_end",
        "started_at",
    )
    search_fields = (
        "provider_subscription_id",
        "customer__user__email",
        "product__name",
        "price__lookup_key",
    )
    list_filter = (
        "status",
        "plan_disabled",
        "cancel_at_period_end",
        "started_at",
        "current_period_end",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    actions = (retry_recurring_charge,)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "provider_payment_method_id",
        "brand",
        "last4",
        "exp_month",
        "exp_year",
        "is_default",
        "active",
        "created_at",
    )
    search_fields = (
        "provider_payment_method_id",
        "customer__user__email",
        "last4",
    )
    list_filter = (
        "is_default",
        "active",
        "brand",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider_checkout_session_id",
        "customer",
        "price",
        "status",
        "completed_at",
        "expires_at",
        "created_at",
    )
    search_fields = (
        "provider_checkout_session_id",
        "customer__user__email",
        "price__lookup_key",
    )
    list_filter = (
        "status",
        "created_at",
        "completed_at",
        "expires_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "subscription",
        "provider_payment_intent_id",
        "amount",
        "currency",
        "status",
        "paid_at",
        "created_at",
    )
    search_fields = (
        "provider_payment_intent_id",
        "customer__user__email",
        "subscription__provider_subscription_id",
    )
    list_filter = (
        "status",
        "currency",
        "paid_at",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    actions = (resend_success_receipt, resend_failure_email)


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "provider_event_id",
        "event_type",
        "processed",
        "created_at",
    )
    search_fields = (
        "provider_event_id",
        "event_type",
    )
    list_filter = (
        "processed",
        "event_type",
        "created_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
