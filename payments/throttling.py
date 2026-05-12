from rest_framework.throttling import UserRateThrottle


class PaymentCheckoutThrottle(UserRateThrottle):
    scope = "payment_checkout"


class PaymentStatusThrottle(UserRateThrottle):
    scope = "payment_status"
