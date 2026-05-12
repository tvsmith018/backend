from django.test import SimpleTestCase

from users.views.generate_id import GenerateIDView
from users.views.login import LoginView
from users.views.password_reset import ResetPasswordView
from users.views.signup import SignupView
from users.views.token_refresh import ThrottledTokenRefreshView


class AuthThrottleViewConfigTests(SimpleTestCase):
    def test_login_view_has_throttle_class(self):
        self.assertTrue(LoginView.throttle_classes)

    def test_signup_view_has_throttle_class(self):
        self.assertTrue(SignupView.throttle_classes)

    def test_otp_view_has_throttle_class(self):
        self.assertTrue(GenerateIDView.throttle_classes)

    def test_password_reset_view_has_throttle_class(self):
        self.assertTrue(ResetPasswordView.throttle_classes)

    def test_token_refresh_view_has_throttle_class(self):
        self.assertTrue(ThrottledTokenRefreshView.throttle_classes)
