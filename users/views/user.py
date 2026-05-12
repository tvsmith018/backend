from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema

from common.openapi import EnvelopeError, EnvelopeSuccess
from common.views.base import AuthenticatedAsyncAPIView
from ..services.auth_service import AuthService

User = get_user_model()


@extend_schema(responses={200: EnvelopeSuccess, 401: EnvelopeError})
class UserView(AuthenticatedAsyncAPIView):

    async def get(self, request):
        user = request.user
        user_data = await sync_to_async(AuthService.get_user)(user.id)
        return self.success({
            "id": user.id,
            "firstname": user_data.firstname,
            "lastname": user_data.lastname,
            "avatar": user_data.avatar.url if user_data.avatar else None
        })

    async def delete(self, request):
        user = request.user
        try:
            delete_status = await sync_to_async(AuthService.delete_user)(user.id)
        except User.DoesNotExist:
            return self.error("User not found.", status=404)
        except Exception:
            return self.error("Unable to delete profile right now.", status=500)

        if delete_status == "superuser_blocked":
            return self.error("Superusers must be deleted manually.", status=403)

        return self.success("Profile deleted successfully.")
