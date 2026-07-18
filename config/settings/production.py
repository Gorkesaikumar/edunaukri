"""Production settings."""

import sys

import environ

from config.logging import get_logging_config
from config.settings.base import *  # noqa: F403
from config.storage_settings import build_storages

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")  # noqa: F405

DEBUG = False

SECRET_KEY = env("SECRET_KEY")
if len(SECRET_KEY) < 50:
    print(
        "ERROR: SECRET_KEY must be at least 50 characters in production.",
        file=sys.stderr,
    )
    sys.exit(1)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {},
    }
}

if env.bool("DB_SSL", default=False):
    DATABASES["default"]["OPTIONS"]["sslmode"] = "require"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,  # noqa: F405
        "OPTIONS": {
            "socket_connect_timeout": 5,   # fail fast if Redis is down
            "socket_timeout": 5,           # read timeout per operation
            "max_connections": 50,         # cap per-process connection pool
        },
        "KEY_PREFIX": "edunaukri",
        "TIMEOUT": 3600,
    }
}

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
WHITENOISE_KEEP_ONLY_HASHED_FILES = False
WHITENOISE_MAX_AGE = 31536000

MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))  # noqa: F405
STORAGES = build_storages(env, BASE_DIR)  # noqa: F405
if env("STORAGE_BACKEND", default="local").lower() == "s3":
    INSTALLED_APPS += ["storages"]  # noqa: F405
    STORAGES["staticfiles"] = {  # noqa: F405
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }
else:
    STORAGES["staticfiles"] = {  # noqa: F405
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    }

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

LOGGING = get_logging_config(debug=False, log_to_file=False)

EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=AUTH_EMAIL_FROM)  # noqa: F405

SPECTACULAR_SETTINGS["SERVE_PERMISSIONS"] = (  # noqa: F405
    ["rest_framework.permissions.AllowAny"]
    if ENABLE_API_DOCS  # noqa: F405
    else ["apps.core.permissions.base.IsPlatformAdmin"]
)
