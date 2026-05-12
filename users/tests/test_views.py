from datetime import date
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase


User = get_user_model()
ATTACHED_IMAGE_PATH = Path(
    r"C:\Users\terrance\.cursor\projects\c-Users-terrance-BigChiefEnt-Offical\assets\c__Users_terrance_AppData_Roaming_Cursor_User_workspaceStorage_5aa478f895ded0d5303101581a79697b_images_134085811072698559-dfbb48c4-d17f-4750-b85c-33fc3ef31576.png"
)


class UserViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="viewer@example.com",
            firstname="View",
            lastname="Tester",
            password="Password123!",
            dob=date(1998, 1, 1),
            bio="bio",
        )

    def test_signup_endpoint_creates_user(self):
        response = self.client.post(
            "/authorized/signup/",
            {
                "email": "fresh@example.com",
                "firstname": "Fresh",
                "lastname": "User",
                "dob": "2001-01-01",
                "password": "FreshPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"], "User registered successfully")
        self.assertTrue(User.objects.filter(email="fresh@example.com").exists())

    @patch("users.services.otp_service.send_email.delay")
    def test_otp_endpoint_returns_code(self, send_email_delay):
        response = self.client.post(
            "/authorized/otp/",
            {
                "email": "brand-new@example.com",
                "otp_type": "signup",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(response.data["data"]["code"]), 6)
        send_email_delay.assert_called_once()

    def test_login_endpoint_returns_tokens(self):
        response = self.client.post(
            "/authorized/login/",
            {
                "email": "viewer@example.com",
                "password": "Password123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_me_endpoint_requires_authentication(self):
        response = self.client.get("/authorized/me/")

        self.assertEqual(response.status_code, 401)

    def test_me_endpoint_returns_user_data_for_authenticated_user(self):
        login_response = self.client.post(
            "/authorized/login/",
            {
                "email": "viewer@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        access_token = login_response.data["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get("/authorized/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["firstname"], "View")
        self.assertEqual(response.data["data"]["lastname"], "Tester")

    def test_logout_blacklists_refresh_token(self):
        login_response = self.client.post(
            "/authorized/login/",
            {
                "email": "viewer@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.post(
            "/authorized/logout/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], "Logged out successfully")

    def test_delete_me_endpoint_deletes_regular_user(self):
        login_response = self.client.post(
            "/authorized/login/",
            {
                "email": "viewer@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        access_token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.delete("/authorized/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"], "Profile deleted successfully.")
        self.assertFalse(User.objects.filter(email="viewer@example.com").exists())

    def test_delete_me_endpoint_blocks_superuser(self):
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            firstname="Admin",
            lastname="User",
            password="Password123!",
            dob=date(1990, 1, 1),
            bio="admin bio",
        )
        login_response = self.client.post(
            "/authorized/login/",
            {
                "email": "admin@example.com",
                "password": "Password123!",
            },
            format="json",
        )
        access_token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.delete("/authorized/me/")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["message"], "Superusers must be deleted manually.")
        self.assertTrue(User.objects.filter(pk=superuser.pk).exists())

    def test_password_reset_updates_password(self):
        response = self.client.post(
            "/authorized/reset-password/",
            {
                "email": "viewer@example.com",
                "password": "NewPassword123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_signup_endpoint_creates_user_with_avatar_multipart(self):
        # Generate a real image buffer so ImageField/Pillow validation always receives valid bytes.
        buf = BytesIO()
        Image.new("RGB", (4, 4), color=(0, 153, 255)).save(buf, format="PNG")
        png_bytes = buf.getvalue()
        avatar = SimpleUploadedFile(
            "attached-image.png",
            png_bytes,
            content_type="image/png",
        )

        response = self.client.post(
            "/authorized/signup/",
            {
                "email": "tvsmith018@gmail.com",
                "firstname": "Terrance",
                "lastname": "Smith",
                "dob": "1989-12-05",
                "password": "FreshPassword123!",
                "avatar": avatar,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["data"], "User registered successfully")
        self.assertTrue(User.objects.filter(email="tvsmith018@gmail.com").exists())

    def test_signup_endpoint_creates_user_with_attached_png_file(self):
        if not ATTACHED_IMAGE_PATH.exists():
            self.skipTest(f"Attached image not found: {ATTACHED_IMAGE_PATH}")

        with ATTACHED_IMAGE_PATH.open("rb") as f:
            avatar = SimpleUploadedFile(
                ATTACHED_IMAGE_PATH.name,
                f.read(),
                content_type="image/png",
            )

        response = self.client.post(
            "/authorized/signup/",
            {
                "email": "tvsmith018+attached@gmail.com",
                "firstname": "Terrance",
                "lastname": "Smith",
                "dob": "1989-12-05",
                "password": "FreshPassword123!",
                "avatar": avatar,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(User.objects.filter(email="tvsmith018+attached@gmail.com").exists())
