from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "auth_login"


class SignupThrottle(AnonRateThrottle):
    scope = "auth_signup"


class OTPThrottle(AnonRateThrottle):
    scope = "auth_otp"


class PasswordResetThrottle(AnonRateThrottle):
    scope = "auth_password_reset"


class TokenRefreshThrottle(AnonRateThrottle):
    scope = "auth_token_refresh"


class PublicWriteThrottle(UserRateThrottle):
    scope = "public_write"
