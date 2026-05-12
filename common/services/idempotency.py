from django.core.cache import cache

def acquire_lock(key, ttl=300):
    return cache.add(key, "1", ttl)