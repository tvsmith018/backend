import random
from django.contrib.auth import get_user_model
from users.tasks.emails import send_email

User = get_user_model()

class OTPService:

    @staticmethod
    def generate(email, otp_type):
        normalized_email = User.objects.normalize_email(str(email).strip()).lower()
        user_exists = User.objects.filter(email__iexact=normalized_email).exists()

        if otp_type == "password-reset" and not user_exists:
            raise ValueError("User does not exist")

        if otp_type == "signup" and user_exists:
            raise ValueError("User already has account")

        code = ''.join(random.choices('0123456789', k=6))
        send_email.delay(normalized_email, code)
        return code