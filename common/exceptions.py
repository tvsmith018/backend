import logging

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler

from common.security_alerts import record_threshold_alert


security_logger = logging.getLogger("security.throttle")


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

    if isinstance(exc, Throttled) or response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        request = context.get("request")
        view = context.get("view")
        user_id = None
        request_path = ""
        request_method = ""
        remote_addr = ""

        if request is not None:
            request_path = request.path
            request_method = request.method
            remote_addr = (
                request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
                or request.META.get("REMOTE_ADDR", "")
            )
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                user_id = user.pk

        security_logger.warning(
            "API rate limit exceeded path=%s method=%s user_id=%s ip=%s view=%s wait=%s",
            request_path,
            request_method,
            user_id,
            remote_addr,
            view.__class__.__name__ if view else None,
            getattr(exc, "wait", None),
        )

        identifier = remote_addr or str(user_id) or "unknown"
        count, crossed_now = record_threshold_alert(
            event_type="throttle",
            identifier=identifier,
            threshold=settings.SECURITY_THROTTLE_ALERT_THRESHOLD,
            window_seconds=settings.SECURITY_ALERT_WINDOW_SECONDS,
        )
        if crossed_now:
            security_logger.error(
                "Throttle spike detected count=%s window_s=%s ip=%s user_id=%s path=%s",
                count,
                settings.SECURITY_ALERT_WINDOW_SECONDS,
                remote_addr,
                user_id,
                request_path,
            )

    return response
