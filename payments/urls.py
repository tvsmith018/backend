from django.urls import path

from payments.api.views import (
    CheckoutSessionStatusView,
    OneTimeCheckoutSessionView,
    RecurringCheckoutSessionView,
    StripeWebhookView,
)


urlpatterns = [
    path("one-time/checkout/", OneTimeCheckoutSessionView.as_view()),
    path("recurring/checkout/", RecurringCheckoutSessionView.as_view()),
    path("checkout/status/", CheckoutSessionStatusView.as_view()),
    path("webhooks/stripe/", StripeWebhookView.as_view()),
]
