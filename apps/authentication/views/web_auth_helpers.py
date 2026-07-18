"""Shared helpers for domain web authentication views."""

from __future__ import annotations

from django.core.exceptions import ValidationError


def format_validation_errors(exc: ValidationError) -> dict[str, str]:
    if getattr(exc, "message_dict", None):
        errors: dict[str, str] = {}
        for key, messages in exc.message_dict.items():
            if isinstance(messages, (list, tuple)) and messages:
                errors[key] = str(messages[0])
            else:
                errors[key] = str(messages)
        return errors
    if getattr(exc, "error_dict", None):
        errors: dict[str, str] = {}
        for key, value in exc.error_dict.items():
            if hasattr(value, "__iter__") and not isinstance(value, str):
                item = value[0]
                if isinstance(item, ValidationError) and getattr(
                    item, "messages", None
                ):
                    errors[key] = str(item.messages[0])
                else:
                    errors[key] = str(item)
            else:
                errors[key] = str(value)
        return errors
    if getattr(exc, "messages", None):
        return {"form": exc.messages[0]}
    return {"form": str(exc)}


def safe_next_url(request) -> str:
    next_url = (request.GET.get("next") or "").strip()
    if request.method == "POST":
        next_url = (request.POST.get("next") or next_url).strip()
    if not next_url.startswith("/") or next_url.startswith("//"):
        return ""
    return next_url


def validate_login_credentials(email: str, password: str) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not email:
        errors["email"] = "Email address is required."
    elif "@" not in email or "." not in email.split("@")[-1]:
        errors["email"] = "Enter a valid email address."
    if not password:
        errors["password"] = "Password is required."
    return errors
