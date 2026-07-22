"""Logging configuration factory for Edunaukri."""

import logging
from pathlib import Path


class RequestContextFilter(logging.Filter):
    """Attach rich request context from thread-local storage to log records."""

    def filter(self, record):
        from apps.core.middleware.request_id import get_request_context

        ctx = get_request_context()
        record.request_id = ctx.get("request_id", "-")
        record.user_id = ctx.get("user_id", "-")
        record.ip_address = ctx.get("ip_address", "-")
        record.request_path = ctx.get("request_path", "-")
        record.status_code = ctx.get("status_code", "-")
        
        # If user_id is "-" but we have a request object, try to extract user dynamically.
        # This handles cases where auth middleware ran AFTER our RequestIDMiddleware.
        if record.user_id == "-":
            try:
                from apps.core.middleware.request_id import _thread_locals
                if hasattr(_thread_locals, "request") and hasattr(_thread_locals.request, "user"):
                    user = _thread_locals.request.user
                    if user and user.is_authenticated:
                        record.user_id = str(user.id)
            except Exception:
                pass

        return True


def get_logging_config(*, debug: bool = False, log_to_file: bool = True) -> dict:
    """Build logging dictConfig for development or production."""
    base_dir = Path(__file__).resolve().parent.parent
    logs_dir = base_dir / "logs"
    if log_to_file:
        logs_dir.mkdir(parents=True, exist_ok=True)

    console_formatter = "verbose" if debug else "json"
    
    # We will log to file in production ALWAYS, and optionally in development.
    # The requirement is to rotate logs automatically.
    
    formatters = {
        "verbose": {
            "format": (
                "{levelname} {asctime} [{request_id}] [User:{user_id}] [IP:{ip_address}] [Path:{request_path}] [Status:{status_code}] "
                "{name} {module} {process:d} {thread:d} {message}"
            ),
            "style": "{",
        },
        "json": {
            "format": (
                '{{"level":"{levelname}","time":"{asctime}",'
                '"request_id":"{request_id}","user_id":"{user_id}",'
                '"ip_address":"{ip_address}","request_path":"{request_path}",'
                '"status_code":"{status_code}","logger":"{name}",'
                '"message":"{message}"}}'
            ),
            "style": "{",
        },
    }

    handlers = ["console"]
    handler_config = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": console_formatter,
            "filters": ["request_context"],
        },
    }

    if log_to_file:
        # Create rotating file handlers for each requested domain
        def _build_file_handler(filename, formatter="json"):
            return {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(logs_dir / filename),
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 10,
                "formatter": formatter,
                "filters": ["request_context"],
            }

        handler_config["django_file"] = _build_file_handler("django.log", console_formatter)
        handler_config["security_file"] = _build_file_handler("security.log", console_formatter)
        handler_config["billing_file"] = _build_file_handler("billing.log", console_formatter)
        handler_config["api_file"] = _build_file_handler("api.log", console_formatter)
        handler_config["audit_file"] = _build_file_handler("audit.log", console_formatter)
        handler_config["errors_file"] = _build_file_handler("errors.log", console_formatter)
        handler_config["errors_file"]["level"] = "ERROR"
        
        handlers.append("django_file")

    loggers = {
        "django": {
            "handlers": ["console", "django_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "django_file", "errors_file"] if log_to_file else ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "django_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "django_file", "errors_file"] if log_to_file else ["console"],
            "level": "DEBUG" if debug else "INFO",
            "propagate": False,
        },
        # Dedicated domain loggers
        "security": {
            "handlers": ["console", "security_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "billing": {
            "handlers": ["console", "billing_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "api": {
            "handlers": ["console", "api_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "audit": {
            "handlers": ["console", "audit_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "resume_trust": {
            "handlers": ["console", "security_file", "errors_file"] if log_to_file else ["console"],
            "level": "INFO",
            "propagate": False,
        },
    }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": "config.logging.RequestContextFilter",
            },
        },
        "formatters": formatters,
        "handlers": handler_config,
        "root": {
            "handlers": handlers,
            "level": "DEBUG" if debug else "INFO",
        },
        "loggers": loggers,
    }
