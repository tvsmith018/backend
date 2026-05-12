from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers.token import UserTokenObtainPairSerializer
from users.throttling import LoginThrottle

class LoginView(TokenObtainPairView):
    serializer_class = UserTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]