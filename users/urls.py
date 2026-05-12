from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from users.views.login import LoginView
from users.views.logout import LogoutView
from users.views.user import UserView
from users.views.signup import SignupView
from users.views.password_reset import ResetPasswordView
from users.views.generate_id import GenerateIDView
from users.views.token_refresh import ThrottledTokenRefreshView


def csrf_exempt_post_only(view):
    """
    CSRF-exempt wrapper for stateless JWT/bootstrap endpoints.

    These routes do not use SessionAuthentication/cookie auth, and are explicitly
    limited to POST (plus OPTIONS for CORS preflight) to reduce CSRF risk surface.
    """
    return csrf_exempt(require_http_methods(["POST", "OPTIONS"])(view))


urlpatterns = [
    path('login/', csrf_exempt_post_only(LoginView.as_view())),
    path('logout/', csrf_exempt_post_only(LogoutView.as_view())),
    path('me/', UserView.as_view()),
    path("signup/", csrf_exempt_post_only(SignupView.as_view())),
    path("otp/", csrf_exempt_post_only(GenerateIDView.as_view())),
    path("reset-password/", csrf_exempt_post_only(ResetPasswordView.as_view())),
    path('token/refresh/', csrf_exempt_post_only(ThrottledTokenRefreshView.as_view()), name='token_refresh'),
]
