import logging

from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import BaseAsyncAPIView
from users.serializers.password_reset import PasswordResetSerializer
from users.services.auth_service import AuthService
from users.throttling import PasswordResetThrottle

logger = logging.getLogger(__name__)


@extend_schema(
    request=PasswordResetSerializer,
    responses={200: EnvelopeSuccess, 400: EnvelopeError},
)
class ResetPasswordView(BaseAsyncAPIView):
    throttle_classes = [PasswordResetThrottle]

    async def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            await sync_to_async(AuthService.reset_password)(
                **serializer.validated_data
            )
            return self.success("Password updated")
        except Exception as e:
            logger.exception(
                "Password reset failed for email=%s",
                serializer.validated_data.get("email"),
            )
            return self.error(str(e))
