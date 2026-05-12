import logging

from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import AuthenticatedAsyncAPIView

logger = logging.getLogger(__name__)


def _blacklist_refresh_token(token_value):
    token = RefreshToken(token_value)
    token.blacklist()


LogoutRequest = inline_serializer(
    name="LogoutRequest",
    fields={"refresh": serializers.CharField()},
)


@extend_schema(
    request=LogoutRequest,
    responses={200: EnvelopeSuccess, 400: EnvelopeError},
)
class LogoutView(AuthenticatedAsyncAPIView):

    async def post(self, request):
        try:
            await sync_to_async(_blacklist_refresh_token)(request.data["refresh"])
            return self.success("Logged out successfully")
        except Exception:
            logger.exception("Logout failed due to invalid refresh token payload")
            return self.error("Invalid refresh token")
