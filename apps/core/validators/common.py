import os
import re

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, URLValidator


def validate_email(value: str) -> None:
    if not value:
        return
    EmailValidator()(value)


def validate_phone(value: str) -> None:
    """Strict phone validation allowing only optional + and 10-15 digits."""
    if not value:
        return
    if not re.match(r"^\+?[0-9]{10,15}$", value.strip()):
        raise ValidationError("Enter a valid phone number (10-15 digits).")


def validate_url(value: str) -> None:
    if not value:
        return
    URLValidator()(value)


def validate_gst(value: str) -> None:
    if not value:
        return
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if not re.match(pattern, str(value).strip().upper()):
        raise ValidationError("Enter a valid GSTIN.")


def validate_pan(value: str) -> None:
    if not value:
        return
    pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
    if not re.match(pattern, str(value).strip().upper()):
        raise ValidationError("Enter a valid PAN.")


def validate_organization_name(value: str) -> None:
    if not value:
        return
    # Basic anti-XSS / script injection prevention
    if re.search(r"<[^>]*>", str(value)) or "script" in str(value).lower():
        raise ValidationError("Organization name contains invalid characters.")


def validate_clean_text(value: str) -> None:
    """Anti-XSS validation for text fields (cover letter, descriptions, etc)."""
    if not value:
        return
    if re.search(r"<(script|iframe|object|embed|applet)[^>]*>", str(value), re.IGNORECASE):
        raise ValidationError("Text contains invalid HTML tags.")


def validate_file_extension(value, allowed_extensions=None) -> None:
    if not value:
        return
    if allowed_extensions is None:
        allowed_extensions = [".pdf", ".doc", ".docx"]
    
    # Handle both string filenames and Django File objects
    filename = str(value)
    if hasattr(value, 'name'):
        filename = value.name

    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file extension. Allowed: {', '.join(allowed_extensions)}")

