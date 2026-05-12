from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from users.services.auth_service import AuthService
from users.services.otp_service import OTPService


User = get_user_model()


class AuthServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="person@example.com",
            firstname="Test",
            lastname="User",
            password="OldPassword123!",
            dob=date(1999, 1, 1),
            bio="bio",
        )

    def test_reset_password_updates_password(self):
        AuthService.reset_password("person@example.com", "NewPassword123!")

        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_reset_password_rejects_existing_password(self):
        with self.assertRaisesMessage(ValueError, "Password already in use"):
            AuthService.reset_password("person@example.com", "OldPassword123!")

    def test_user_exists_normalizes_email(self):
        self.assertTrue(AuthService.user_exists("  PERSON@example.com  "))
        self.assertFalse(AuthService.user_exists("missing@example.com"))


class OTPServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="member@example.com",
            firstname="Member",
            lastname="User",
            password="Password123!",
            dob=date(2000, 2, 2),
            bio="bio",
        )

    @patch("users.services.otp_service.send_email.delay")
    def test_generate_signup_code_enqueues_email(self, send_email_delay):
        code = OTPService.generate("new-user@example.com", "signup")

        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        send_email_delay.assert_called_once_with("new-user@example.com", code)

    def test_generate_signup_code_rejects_existing_user(self):
        with self.assertRaisesMessage(ValueError, "User already has account"):
            OTPService.generate("member@example.com", "signup")

    def test_generate_password_reset_rejects_missing_user(self):
        with self.assertRaisesMessage(ValueError, "User does not exist"):
            OTPService.generate("missing@example.com", "password-reset")
