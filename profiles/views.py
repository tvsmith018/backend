from asgiref.sync import sync_to_async
from drf_spectacular.utils import extend_schema

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import AuthenticatedAsyncAPIView

from profiles.services.profile_service import ProfileService


@extend_schema(responses={200: EnvelopeSuccess, 401: EnvelopeError})
class ProfileMeView(AuthenticatedAsyncAPIView):
    async def get(self, request):
        data = await sync_to_async(ProfileService.get_profile_me)(request.user.id)
        return self.success(data)
