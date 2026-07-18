"""Field-level validators for the Company Management module.

These wrap the shared core validators and add company-specific rules
(founded year bounds, social-link host checks, branding file-type checks).
"""

import datetime

from django.core.exceptions import ValidationError

from apps.core.validators.common import (
    validate_email as _validate_email,
    validate_gst as _validate_gst,
    validate_phone as _validate_phone,
    validate_url as _validate_url,
)
from apps.documents.constants.enums import StorageFileStatus, StorageFileType

validate_company_email = _validate_email
validate_company_phone = _validate_phone
validate_company_website = _validate_url
validate_gst_number = _validate_gst


_SOCIAL_HOSTS = {
    "linkedin_url": "linkedin.com",
    "twitter_url": ("twitter.com", "x.com"),
    "facebook_url": "facebook.com",
    "instagram_url": "instagram.com",
    "youtube_url": ("youtube.com", "youtu.be"),
}


def validate_founded_year(value) -> None:
    if value is None:
        return
    current_year = datetime.date.today().year
    if value < 1800 or value > current_year:
        raise ValidationError(f"Founded year must be between 1800 and {current_year}.")


def validate_social_link(value: str, *, field: str) -> None:
    """Validate a social URL and ensure it points at the expected platform host."""
    if not value:
        return
    _validate_url(value)
    expected = _SOCIAL_HOSTS.get(field)
    if not expected:
        return
    hosts = expected if isinstance(expected, tuple) else (expected,)
    lowered = value.lower()
    if not any(host in lowered for host in hosts):
        raise ValidationError(
            f"URL does not look like a valid {field.replace('_url', '')} link."
        )


def validate_branding_file(stored_file, *, expected_type: StorageFileType) -> None:
    """Ensure a stored file is a usable branding asset (logo/banner)."""
    if stored_file is None:
        raise ValidationError("Branding file not found.")
    if stored_file.is_deleted or stored_file.status != StorageFileStatus.ACTIVE:
        raise ValidationError("Branding file is not available.")
    if stored_file.file_type != expected_type:
        raise ValidationError("Invalid branding file type.")


def validate_logo_file(stored_file) -> None:
    validate_branding_file(stored_file, expected_type=StorageFileType.COMPANY_LOGO)


def validate_banner_file(stored_file) -> None:
    validate_branding_file(stored_file, expected_type=StorageFileType.COMPANY_LOGO)
