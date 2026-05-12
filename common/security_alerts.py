import time

from django.core.cache import cache


def _bucket_for(window_seconds: int) -> int:
    return int(time.time()) // window_seconds


def _aggregate_key(event_type: str, window_seconds: int) -> str:
    return f"security:{event_type}:aggregate:{_bucket_for(window_seconds)}"


def get_recent_event_count(*, event_type: str, window_seconds: int) -> int:
    if window_seconds <= 0:
        return 0
    return int(cache.get(_aggregate_key(event_type, window_seconds), 0) or 0)


def record_threshold_alert(
    *,
    event_type: str,
    identifier: str,
    threshold: int,
    window_seconds: int,
) -> tuple[int, bool]:
    """
    Count security events in a time window and return (count, threshold_crossed_now).
    """
    if threshold <= 0 or window_seconds <= 0:
        return 0, False

    bucket = _bucket_for(window_seconds)
    key = f"security:{event_type}:{identifier}:{bucket}"
    alert_key = f"{key}:alerted"
    aggregate_key = _aggregate_key(event_type, window_seconds)

    added = cache.add(key, 1, timeout=window_seconds)
    count = 1 if added else cache.incr(key)
    aggregate_added = cache.add(aggregate_key, 1, timeout=window_seconds)
    if not aggregate_added:
        cache.incr(aggregate_key)

    crossed_now = count >= threshold and cache.add(alert_key, 1, timeout=window_seconds)
    return count, bool(crossed_now)
