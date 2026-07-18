"""Development settings."""

from config.settings.base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Always use project-local media in development (ignore Docker paths from .env)
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}


def _redis_available(redis_url):
    try:
        import redis

        client = redis.from_url(redis_url)
        client.ping()
        return True
    except Exception:
        return False


if REDIS_URL and _redis_available(REDIS_URL):  # noqa: F405
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,  # noqa: F405
        }
    }
    CHANNEL_LAYERS = {  # noqa: F811
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},  # noqa: F405
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
    CHANNEL_LAYERS = {  # noqa: F811
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [  # noqa: F405
    "apps.core.renderers.EnvelopeJSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")  # noqa: F405

import sys

LOGGING = get_logging_config(
    debug=True,
    log_to_file=not any("test" in arg or "pytest" in arg for arg in sys.argv),
)  # noqa: F405
