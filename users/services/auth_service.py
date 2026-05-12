from django.contrib.auth import get_user_model

User = get_user_model()

class AuthService:

    @staticmethod
    def reset_password(email, password):
        user = User.objects.get(email=email)
        if user.check_password(password):
            raise ValueError("Password already in use")
        user.set_password(password)
        user.save()

    @staticmethod
    def user_exists(email: str) -> bool:
        """
        Normalize the email the same way everywhere.
        """
        normalized = (email or "").strip().lower()
        return User.objects.filter(email__iexact=normalized).exists()
    
    @staticmethod
    def get_user(pk: int) -> object:
        return User.objects.get(pk=pk)

    @staticmethod
    def delete_user(pk: int) -> str:
        user = User.objects.get(pk=pk)
        if user.is_superuser:
            return "superuser_blocked"
        user.delete()
        return "deleted"