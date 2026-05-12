import logging

from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import BaseAsyncAPIView
from users.serializers.otp import OTPSerializer
from users.services.otp_service import OTPService
from users.throttling import OTPThrottle

logger = logging.getLogger(__name__)


@extend_schema(
    request=OTPSerializer,
    responses={202: EnvelopeSuccess, 400: EnvelopeError, 404: EnvelopeError},
)
class GenerateIDView(BaseAsyncAPIView):
    throttle_classes = [OTPThrottle]

    async def post(self, request):
        serializer = await sync_to_async(OTPSerializer)(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            code = await sync_to_async(OTPService.generate)(**serializer.validated_data)
            return self.success({"code": code}, 202)
        except ValueError as e:
            logger.warning(
                "OTP generation blocked for email=%s otp_type=%s",
                serializer.validated_data.get("email"),
                serializer.validated_data.get("otp_type"),
            )
            return self.error(str(e), 404)
