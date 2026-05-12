from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


# -----------------------
# Base Model
# -----------------------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# -----------------------
# Billing Customer
# -----------------------
class BillingCustomer(TimeStampedModel):
    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_customer",
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.STRIPE,
    )
    provider_customer_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_customers"

    def __str__(self):
        return f"{self.user_id} - {self.provider_customer_id}"


# -----------------------
# Product
# -----------------------
class BillingProduct(TimeStampedModel):
    class ProductType(models.TextChoices):
        SUBSCRIPTION = "subscription", "Subscription"
        ONE_TIME = "one_time", "One Time"

    name = models.CharField(max_length=255)
    code = models.SlugField(max_length=100, unique=True)
    provider_product_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.SUBSCRIPTION,
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_products"

    def __str__(self):
        return self.name


# -----------------------
# Price
# -----------------------
class BillingPrice(TimeStampedModel):
    class Interval(models.TextChoices):
        DAY = "day", "Day"
        WEEK = "week", "Week"
        MONTH = "month", "Month"
        YEAR = "year", "Year"

    class PriceType(models.TextChoices):
        RECURRING = "recurring", "Recurring"
        ONE_TIME = "one_time", "One Time"

    product = models.ForeignKey(
        BillingProduct,
        on_delete=models.CASCADE,
        related_name="prices",
    )
    lookup_key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    provider_price_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    price_type = models.CharField(
        max_length=20,
        choices=PriceType.choices,
        default=PriceType.RECURRING,
    )
    unit_amount = models.PositiveIntegerField(
        help_text="Amount in cents"
    )
    currency = models.CharField(max_length=10, default="usd")
    recurring_interval = models.CharField(
        max_length=20,
        choices=Interval.choices,
        blank=True,
        null=True,
    )
    interval_count = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_prices"

    def __str__(self):
        return self.lookup_key


# -----------------------
# Subscription
# -----------------------
class Subscription(TimeStampedModel):
    class Status(models.TextChoices):
        INCOMPLETE = "incomplete", "Incomplete"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELED = "canceled", "Canceled"
        UNPAID = "unpaid", "Unpaid"

    customer = models.ForeignKey(
        BillingCustomer,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    product = models.ForeignKey(
        BillingProduct,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    price = models.ForeignKey(
        BillingPrice,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    provider_subscription_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.INCOMPLETE,
    )
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)
    plan_disabled = models.BooleanField(default=False)
    plan_disabled_reason = models.CharField(max_length=100, blank=True)
    plan_disabled_attempt_count = models.PositiveIntegerField(default=0)
    plan_disabled_at = models.DateTimeField(blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=Q(status__in=["incomplete", "active", "past_due"]),
                name="unique_open_subscription_per_customer",
            )
        ]

    def __str__(self):
        return self.provider_subscription_id


# -----------------------
# Payment Method
# -----------------------
class PaymentMethod(TimeStampedModel):
    customer = models.ForeignKey(
        BillingCustomer,
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    provider_payment_method_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    brand = models.CharField(max_length=50, blank=True)
    last4 = models.CharField(max_length=4, blank=True)
    exp_month = models.PositiveSmallIntegerField(blank=True, null=True)
    exp_year = models.PositiveSmallIntegerField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_payment_methods"

    def __str__(self):
        return self.provider_payment_method_id


# -----------------------
# Checkout Session
# -----------------------
class CheckoutSession(TimeStampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETE = "complete", "Complete"
        EXPIRED = "expired", "Expired"

    customer = models.ForeignKey(
        BillingCustomer,
        on_delete=models.CASCADE,
        related_name="checkout_sessions",
        null=True,
        blank=True,
    )
    price = models.ForeignKey(
        BillingPrice,
        on_delete=models.PROTECT,
        related_name="checkout_sessions",
        null=True,
        blank=True,
    )
    provider_checkout_session_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    checkout_url = models.URLField(max_length=1000, blank=True)
    success_url = models.URLField(max_length=1000, blank=True)
    cancel_url = models.URLField(max_length=1000, blank=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_checkout_sessions"

    def __str__(self):
        return self.provider_checkout_session_id


# -----------------------
# Payment Record
# -----------------------
class PaymentRecord(TimeStampedModel):
    class Status(models.TextChoices):
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        PROCESSING = "processing", "Processing"

    customer = models.ForeignKey(
        BillingCustomer,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
        blank=True,
    )
    provider_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
    )
    amount = models.PositiveIntegerField()
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.PROCESSING,
    )
    paid_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_payments"

    def __str__(self):
        return f"{self.amount} {self.currency}"


# -----------------------
# Webhook Event
# -----------------------
class WebhookEvent(TimeStampedModel):
    provider_event_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    event_type = models.CharField(max_length=255)
    processed = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_webhook_events"

    def __str__(self):
        return self.event_type
