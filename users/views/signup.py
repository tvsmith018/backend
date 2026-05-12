import logging

from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import BaseAsyncAPIView
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from users.serializers.signup import SignupSerializer
from users.throttling import SignupThrottle

logger = logging.getLogger(__name__)


def _signup_payload_for_serializer(request):
    """
    Build serializer input from parsed body + Django FILES.

    Under ASGI + async views, multipart files sometimes land only on the underlying
    HttpRequest.FILES and are missing from request.data; merging avoids dropped avatars.

    Also normalize scalar fields: ``dict(request.data)`` can yield one-element lists or
    bytes for multipart parts; DRF CharField/EmailField then fail with "Not a valid string"
    / "Enter a valid email address" even when the client sent correct text.
    """
    django_request = getattr(request, "_request", request)
    encoding = getattr(django_request, "encoding", None) or "utf-8"
    raw = request.data

    if hasattr(raw, "dict"):
        payload = raw.dict()
    else:
        payload = {key: raw[key] for key in raw}

    files = getattr(django_request, "FILES", None) or {}

    for key, file_handle in files.items():
        payload[key] = file_handle

    for key, val in list(payload.items()):
        if key in files:
            continue
        if hasattr(val, "read"):
            continue
        if key == "avatar" and val in [None, "", "null", "undefined"]:
            payload[key] = None
            continue
        if isinstance(val, (list, tuple)):
            val = val[0] if len(val) == 1 else val
        if isinstance(val, bytes):
            val = val.decode(encoding)
        elif val is not None and not isinstance(val, str):
            val = str(val)
        payload[key] = val

    return payload


@extend_schema(
    request=SignupSerializer,
    responses={201: EnvelopeSuccess, 400: EnvelopeError},
)
class SignupView(BaseAsyncAPIView):
    throttle_classes = [SignupThrottle]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _post_sync(self, request):
        """Run parse + validation + save on a worker thread (avoids ASGI/async + multipart quirks)."""
        django_request = getattr(request, "_request", request)
        payload = _signup_payload_for_serializer(request)
        serializer = SignupSerializer(data=payload)
        logger.info(
            "Signup request source ua=%s x_signup_client=%s",
            django_request.META.get("HTTP_USER_AGENT"),
            django_request.META.get("HTTP_X_SIGNUP_CLIENT"),
        )
        if not serializer.is_valid(raise_exception=False):
            logger.warning(
                "Signup validation failed email=%s errors=%s",
                payload.get("email"),
                serializer.errors,
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            serializer.save()
        except Exception as e:
            logger.exception("Signup failed for email=%s", payload.get("email"))
            return self.error(str(e))
        return self.success("User registered successfully", 201)

    async def post(self, request):
        return await sync_to_async(self._post_sync)(request)
