from urllib.parse import parse_qs

from channels.db import database_sync_to_async
@database_sync_to_async
def _get_user_for_token(token_value):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
    from rest_framework_simplejwt.tokens import AccessToken
    from users.services.auth_service import AuthService

    try:
        validated_token = AccessToken(token_value)
        user_id = validated_token.get("user_id")
        if not user_id:
            return AnonymousUser()
        return AuthService.get_user(user_id)
    except (InvalidToken, TokenError, Exception):
        return AnonymousUser()


class JwtAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from django.contrib.auth.models import AnonymousUser

        query_params = parse_qs(scope.get("query_string", b"").decode())
        token = (query_params.get("token") or [None])[0]
        scope["user"] = AnonymousUser()
        if token:
            scope["user"] = await _get_user_for_token(token)
        return await self.inner(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)
