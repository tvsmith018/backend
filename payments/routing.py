from django.urls import re_path

from payments.consumers import PaymentStatusConsumer


websocket_urlpatterns = [
    re_path(r"ws/payments/$", PaymentStatusConsumer.as_asgi()),
]
