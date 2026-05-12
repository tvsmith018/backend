from .settings import *  # noqa: F403,F401


DEBUG = False
IS_PRODUCTION = False
SECRET_KEY = "test-secret-key"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
PAYMENT_RETURN_URL_ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1", "example.com"]
CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = []
GRAPHQL_ENABLE_GRAPHIQL = False
OTEL_INSTRUMENTATION_ENABLED = False
SENTRY_ENABLED = False
API_DOCS_ENABLED = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "backend-tests",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
