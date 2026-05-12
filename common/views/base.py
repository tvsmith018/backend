from adrf.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework.response import Response


class BaseAsyncAPIView(APIView):
    permission_classes = [AllowAny]

    def success(self, data=None, status=200):
        return Response({"success": True, "data": data}, status=status)

    def error(self, message, status=400):
        return Response({"success": False, "message": message}, status=status)
    
class AuthenticatedAsyncAPIView(BaseAsyncAPIView):
    authentication_classes = [JWTStatelessUserAuthentication]
    permission_classes = [IsAuthenticated]