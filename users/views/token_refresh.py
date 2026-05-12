from rest_framework_simplejwt.views import TokenRefreshView

from users.throttling import TokenRefreshThrottle


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [TokenRefreshThrottle]
