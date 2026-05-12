from django.core.cache import cache

def get_or_set(key, ttl, fn):
    data = cache.get(key)
    if data is None:
        data = fn()
        cache.set(key, data, ttl)
    return data