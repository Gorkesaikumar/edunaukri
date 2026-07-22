"""Base Django settings shared across all environments."""

import sys
from datetime import timedelta
from pathlib import Path

import environ

from config.logging import get_logging_config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DB_SSL=(bool, False),
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES=(int, 15),
    JWT_REFRESH_TOKEN_LIFETIME_DAYS=(int, 7),
    ENABLE_API_DOCS=(bool, True),
    TIME_ZONE=(str, "Asia/Kolkata"),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-dev-only-change-for-production-min-50-chars!!",
)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = env.bool("CORS_ALLOW_CREDENTIALS", default=True)
if DEBUG and not CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ]

DJANGO_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "channels",
    "django_celery_beat",
]

LOCAL_APPS = [
    # Kernel
    "apps.core",
    "apps.common",
    # Identity & auth
    "apps.accounts",
    "apps.authentication",
    "apps.social_auth",
    # Shared infrastructure
    "apps.documents",
    "apps.search",
    "apps.audit",
    "apps.notifications",
    # IT domain
    "apps.it_recruitment",
    "apps.companies",
    "apps.jobs",
    # Faculty domain
    "apps.academic_recruitment",
    "apps.colleges",
    "apps.faculty",
    # Cross-domain
    "apps.applications",
    "apps.resume_trust",
    "apps.billing",
    "apps.invoices",
    "apps.guarantee_claims",
    "apps.reports",
    "apps.dashboard",
    "apps.admin_panel",
    # API & ops
    "apps.api",
    "apps.health",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.request_id.RequestIDMiddleware",
    "apps.core.middleware.timezone.TimezoneMiddleware",
    "apps.core.middleware.request_logging.RequestLoggingMiddleware",
    "apps.core.middleware.audit_context.AuditContextMiddleware",
    "apps.core.middleware.security_headers.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.authentication.middleware.web_it_user.WebITUserMiddleware",
    "apps.authentication.middleware.uuid_route_guard.UUIDRouteAuthorizationMiddleware",
    "apps.authentication.middleware.session_security.SessionSecurityMiddleware",
    "apps.authentication.middleware.web_auth_guard.WebAuthGuardMiddleware",
    "apps.core.middleware.maintenance.MaintenanceModeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.ratelimit_middleware.RatelimitExceptionMiddleware",
    "apps.core.middleware.exception_middleware.ExceptionMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.authentication.context_processors.navigation.navigation",
                "apps.core.context_processors.platform_config",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.AdminUser"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.authentication.backends.AdminUserAuthBackend",
    "apps.accounts.authentication.backends.ITUserAuthBackend",
    "apps.accounts.authentication.backends.ProfessorUserAuthBackend",
    "apps.accounts.authentication.backends.CollegeUserAuthBackend",
    "apps.accounts.authentication.backends.FacultyUserAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = env("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ADMIN_URL = env("ADMIN_URL", default="admin/")

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "apps.accounts.authentication.jwt.DomainJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "apps.core.renderers.EnvelopeJSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "EXCEPTION_HANDLER": "apps.core.exceptions.handlers.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "30/hour",
        "login": "20/hour",
        "login_ip": "10/min",
        "auth_registration": "10/hour",
        "auth_password_reset": "10/hour",
        "auth_password_change": "20/hour",
        "auth_email_verify": "30/hour",
        "auth_token_refresh": "60/hour",
        "auth_admin": "60/hour",
        "otp": "10/min",
        "search": "120/hour",
        "search_anon": "60/hour",
        "applications": "300/hour",
        "resume_upload": "10/hour",
        "invoices": "300/hour",
        "dashboard": "1000/hour",
        "reports": "60/hour",
        "notifications": "2000/hour",
        "brute_force_ip": "100/min",
    },
}

# Cache & Rate Limiting (django-ratelimit)
RATELIMIT_ENABLE = env.bool("RATELIMIT_ENABLE", default=True)
RATELIMIT_USE_CACHE = "default"

_REDIS_URL = env.str("REDIS_URL", default="")

if _REDIS_URL:
    # Django 4.0+ built-in Redis cache backend — no extra package required
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _REDIS_URL,
            "OPTIONS": {
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "max_connections": 50,
            },
            "KEY_PREFIX": "edunaukri",
            "TIMEOUT": 3600,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env("JWT_ACCESS_TOKEN_LIFETIME_MINUTES")
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env("JWT_REFRESH_TOKEN_LIFETIME_DAYS")),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Edunaukri API",
    "DESCRIPTION": (
        "Unified recruitment platform API serving IT Recruitment and "
        "Engineering Faculty Recruitment domains under separate authentication systems."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "TAGS": [
        {"name": "auth-jwt", "description": "JWT token issuance and refresh"},
        {
            "name": "auth-registration",
            "description": "Domain-specific user registration",
        },
        {"name": "auth-password", "description": "Password reset and change"},
        {"name": "auth-verification", "description": "Email verification"},
        {"name": "auth-session", "description": "Session-based login and logout"},
        {"name": "auth-profile", "description": "Authenticated user context"},
        {"name": "auth-admin", "description": "Admin user lifecycle management"},
        {"name": "auth", "description": "Authentication endpoints (legacy tag)"},
        {"name": "health", "description": "Health and readiness probes"},
        {"name": "accounts-profiles", "description": "Unified profile management"},
        {"name": "it-recruitment", "description": "IT companies and job postings"},
        {"name": "companies", "description": "Company management for recruiters"},
        {
            "name": "admin-companies",
            "description": "Admin oversight and verification of companies",
        },
        {
            "name": "jobs",
            "description": "Enterprise job management for recruiters and public discovery",
        },
        {"name": "admin-jobs", "description": "Admin oversight and moderation of jobs"},
        {
            "name": "faculty-vacancies",
            "description": "Enterprise faculty vacancy management for colleges and public discovery",
        },
        {
            "name": "admin-faculty-vacancies",
            "description": "Admin oversight and moderation of faculty vacancies",
        },
        {"name": "it-applications", "description": "IT job applications"},
        {
            "name": "faculty-recruitment",
            "description": "Faculty vacancies and colleges",
        },
        {
            "name": "institutions",
            "description": "College / institution management for college users",
        },
        {
            "name": "admin-institutions",
            "description": "Admin oversight and verification of institutions",
        },
        {"name": "faculty-applications", "description": "Faculty job applications"},
        {
            "name": "admin-recruitment",
            "description": "Admin oversight for jobs and applications",
        },
        {
            "name": "billing",
            "description": "Placement fees and fee schedule configuration",
        },
        {
            "name": "invoices",
            "description": "Invoice lifecycle, payments, and financial summary",
        },
        {
            "name": "guarantee-claims",
            "description": "Placement guarantee claims and resolutions",
        },
        {
            "name": "admin-panel",
            "description": "Enterprise admin panel — dashboard, users, moderation, billing, reports, audit",
        },
        {
            "name": "search",
            "description": "Unified search, filtering, sorting, and pagination across domains",
        },
    ],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "SessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "sessionid",
            },
        }
    },
    "ENUM_NAME_OVERRIDES": {
        "DomainEnum": "apps.core.constants.enums.DomainType",
        "EmploymentTypeEnum": "apps.jobs.constants.enums.EmploymentType",
        "StatusEnum": "apps.jobs.constants.enums.JobStatus",
        "PreferredQualificationEnum": "apps.faculty.constants.enums.QualificationLevel",
    },
    "SCHEMA_COERCE_PATH_PK": True,
    "SECURITY": [{"BearerAuth": []}, {"SessionAuth": []}],
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
}

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/2")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_RESULT_EXPIRES = 86400
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600, "max_connections": 100}
CELERY_REDIS_MAX_CONNECTIONS = 100

# Authentication security
AUTH_MAX_FAILED_LOGIN_ATTEMPTS = env.int("AUTH_MAX_FAILED_LOGIN_ATTEMPTS", default=5)
AUTH_LOCKOUT_MINUTES = env.int("AUTH_LOCKOUT_MINUTES", default=30)
AUTH_REQUIRE_EMAIL_VERIFICATION = env.bool(
    "AUTH_REQUIRE_EMAIL_VERIFICATION", default=False
)
AUTH_EMAIL_DELIVERY_ENABLED = env.bool("AUTH_EMAIL_DELIVERY_ENABLED", default=False)
AUTH_EMAIL_FROM = env("AUTH_EMAIL_FROM", default="noreply@edunaukari.com")
AUTH_FRONTEND_BASE_URL = env("AUTH_FRONTEND_BASE_URL", default="http://localhost:3000")
WEB_BASE_URL = env("WEB_BASE_URL", default="http://127.0.0.1:8000")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=AUTH_EMAIL_FROM)

# OAuth (Google / LinkedIn) — IT web sign-in
OAUTH_REDIRECT_BASE = env("OAUTH_REDIRECT_BASE", default="http://127.0.0.1:8000")
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
LINKEDIN_OAUTH_CLIENT_ID = env("LINKEDIN_OAUTH_CLIENT_ID", default="")
LINKEDIN_OAUTH_CLIENT_SECRET = env("LINKEDIN_OAUTH_CLIENT_SECRET", default="")

CELERY_BEAT_SCHEDULE = {
    "process-outbox-every-minute": {
        "task": "notifications.process_outbox",
        "schedule": 60.0,
        "kwargs": {"batch_size": 50},
    },
    "mark-overdue-invoices-hourly": {
        "task": "invoices.mark_overdue",
        "schedule": 3600.0,
        "kwargs": {"batch_size": 100},
    },
    "scan-upcoming-interviews-every-15-minutes": {
        "task": "applications.scan_upcoming_interviews",
        "schedule": 900.0,
    },
    "scan-expiring-certificates-daily": {
        "task": "it_recruitment.scan_expiring_certificates",
        "schedule": 86400.0,
    },
    "scan-expiring-professor-certificates-daily": {
        "task": "academic_recruitment.scan_expiring_certificates",
        "schedule": 86400.0,
    },
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

ENABLE_API_DOCS = env("ENABLE_API_DOCS")

# Security baseline
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REDIRECT_EXEMPT = [r"^api/v[0-9]/health/.*", r"^health/.*"]
X_FRAME_OPTIONS = "DENY"
CSRF_COOKIE_HTTPONLY = True
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", default="Lax")
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=60 * 60 * 8)
SESSION_SAVE_EVERY_REQUEST = env.bool("SESSION_SAVE_EVERY_REQUEST", default=True)
SESSION_EXPIRE_AT_BROWSER_CLOSE = env.bool(
    "SESSION_EXPIRE_AT_BROWSER_CLOSE", default=False
)

# JWT HttpOnly cookies for server-rendered web authentication (IT domain)
JWT_ACCESS_COOKIE_NAME = env("JWT_ACCESS_COOKIE_NAME", default="edunaukri_access")
JWT_REFRESH_COOKIE_NAME = env("JWT_REFRESH_COOKIE_NAME", default="edunaukri_refresh")
JWT_REFRESH_COOKIE_PATH = env("JWT_REFRESH_COOKIE_PATH", default="/")
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=not DEBUG)
JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", default="Lax")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = get_logging_config(
    debug=DEBUG,
    log_to_file=not any("test" in arg or "pytest" in arg for arg in sys.argv),
)

# ─────────────────────────────────────────────────────────────────────────────
# Resume Trust & Fraud Detection Engine — Configuration
# All thresholds, weights, and scoring parameters live here.
# No values are hardcoded in the engine or rule classes.
# ─────────────────────────────────────────────────────────────────────────────
RESUME_TRUST_ENGINE = {
    # ── Severity → base penalty mapping (used when a rule does not set its own weight)
    "SEVERITY_WEIGHTS": {
        "LOW": 5,
        "MEDIUM": 15,
        "HIGH": 30,
        "CRITICAL": 50,
    },

    # ── Category → weight multiplier (0.0–2.0).
    # Controls how much each category's penalty contributes to the overall risk score.
    # 1.0 = equal weight; 2.0 = double impact; 0.5 = half impact.
    "CATEGORY_WEIGHTS": {
        "Timeline":          1.5,
        "Education":         1.5,
        "Skills":            1.0,
        "Content Integrity": 1.0,
        "Contact":           1.2,
        "Completeness":      0.8,
        "Employment":        1.3,
        "Certifications":    1.0,
    },

    # ── Risk level thresholds (applied to the final weighted risk score 0–100)
    "RISK_THRESHOLDS": {
        "CRITICAL": 70,
        "HIGH":     40,
        "MEDIUM":   15,
    },

    # ── Confidence scoring parameters
    "BASE_CONFIDENCE_NO_WARNINGS":    0.95,
    "BASE_CONFIDENCE_WITH_WARNINGS":  1.00,
    "CONFIDENCE_PENALTY_PER_WARNING": 0.02,
    "MIN_CONFIDENCE":                 0.40,

    # ── Rule-level weight overrides (rule_code → penalty override).
    # Override a rule's DEFAULT_WEIGHT without touching rule code.
    "RULE_WEIGHT_OVERRIDES": {
        # "TIMELINE_001": 35,
    },

    # ── Popup Warning Threshold
    # If trust_score < POPUP_TRUST_THRESHOLD (default 70), a respectful warning popup is shown once per resume version
    "POPUP_TRUST_THRESHOLD": 70,

    # ── Human-readable recommendation messages keyed by recommendation value
    "RECOMMENDATION_MESSAGES": {
        "PASS": (
            "Resume passed all automated checks. Candidate may proceed to the next stage."
        ),
        "FLAG_FOR_REVIEW": (
            "Resume has been flagged for manual review. "
            "Verify the highlighted sections with the candidate before proceeding."
        ),
        "REJECT": (
            "Resume failed critical trust checks. "
            "This candidate should not proceed without thorough background verification."
        ),
    },
}
