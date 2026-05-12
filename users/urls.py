from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from users.views.login import LoginView
from users.views.logout import LogoutView
from users.views.user import UserView
from users.views.signup import SignupView
from users.views.password_reset import ResetPasswordView
from users.views.generate_id import GenerateIDView
from users.views.token_refresh import ThrottledTokenRefreshView

urlpatterns = [
    path('login/', csrf_exempt(LoginView.as_view())),
    path('logout/', csrf_exempt(LogoutView.as_view())),
    path('me/', UserView.as_view()),
    path("signup/", csrf_exempt(SignupView.as_view())),
    path("otp/", csrf_exempt(GenerateIDView.as_view())),
    path("reset-password/", csrf_exempt(ResetPasswordView.as_view())),
    path('token/refresh/', csrf_exempt(ThrottledTokenRefreshView.as_view()), name='token_refresh'),
]
