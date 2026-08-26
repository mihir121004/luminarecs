"""Self-contained settings used by the automated test suite."""

from .settings import *  # noqa: F403

DEBUG = True
SECRET_KEY = "test-only-secret-key-not-for-production"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
