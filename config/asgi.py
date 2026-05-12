"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from common.auth_channels import JwtAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django_asgi_app = get_asgi_application()

from comments.routing import websocket_urlpatterns
from payments.routing import websocket_urlpatterns as payment_websocket_urlpatterns
from profiles.routing import websocket_urlpatterns as profile_websocket_urlpatterns
from articles.routing import websocket_urlpatterns as article_websocket_urlpatterns

# application = get_asgi_application()

allowed_websocket_origins = [
    "https://www.bigchiefnewz.com",
    "https://bigchiefnewz.com",
    "https://bigchiefnewz-a2e8434d1e6d.herokuapp.com",
    "https://bigchiefdev.ngrok.app",
]

extra_allowed_origins = os.environ.get("WEBSOCKET_ALLOWED_ORIGINS", "")
for origin in [item.strip() for item in extra_allowed_origins.split(",") if item.strip()]:
    if origin not in allowed_websocket_origins:
        allowed_websocket_origins.append(origin)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket":OriginValidator(
        JwtAuthMiddlewareStack(
            URLRouter(
                article_websocket_urlpatterns
                + websocket_urlpatterns
                + payment_websocket_urlpatterns
                + profile_websocket_urlpatterns
            )
        ),
        allowed_websocket_origins,
    ),
    # Just HTTP for now. (We can add other protocols later.)
})
