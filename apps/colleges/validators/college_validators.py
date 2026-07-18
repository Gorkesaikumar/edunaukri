"""Field-level validators for the College / Institution Management module."""

import datetime
import re

from django.core.exceptions import ValidationError

from apps.core.validators.common import (
    validate_email as _validate_email,
    validate_phone as _validate_phone,
    validate_url as _validate_url,
)
from apps.documents.constants.enums import StorageFileStatus, StorageFileType

validate_institution_email = _validate_email
validate_institution_phone = _validate_phone
validate_institution_website = _validate_url


_SOCIAL_HOSTS = {
    "linkedin_url": "linkedin.com",
    "facebook_url": "facebook.com",
    "instagram_url": "instagram.com",
    "twitter_url": ("twitter.com", "x.com"),
    "youtube_url": ("youtube.com", "youtu.be"),
}

_POSTAL_CODE_RE = re.compile(r"^\d{4,10}$")
_ACCREDITATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-/ ]{1,49}$")


def validate_postal_code(value: str) -> None:
    if not value:
        return
    if not _POSTAL_CODE_RE.match(value.strip()):
        raise ValidationError("Enter a valid postal code (4-10 digits).")


def validate_established_year(value) -> None:
    if value is None:
        return
    current_year = datetime.date.today().year
    if value < 1800 or value > current_year:
        raise ValidationError(
            f"Established year must be between 1800 and {current_year}."
        )


def validate_accreditation_number(
    value: str, *, label: str = "Accreditation number"
) -> None:
    """Approval / accreditation identifiers (AICTE, UGC, NBA, etc.)."""
    if not value:
        return
    if not _ACCREDITATION_RE.match(value.strip()):
        raise ValidationError(f"Enter a valid {label}.")


def validate_latitude(value) -> None:
    if value is None:
        return
    if not (-90 <= float(value) <= 90):
        raise ValidationError("Latitude must be between -90 and 90.")


def validate_longitude(value) -> None:
    if value is None:
        return
    if not (-180 <= float(value) <= 180):
        raise ValidationError("Longitude must be between -180 and 180.")


def validate_social_link(value: str, *, field: str) -> None:
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
    if stored_file is None:
        raise ValidationError("Branding file not found.")
    if stored_file.is_deleted or stored_file.status != StorageFileStatus.ACTIVE:
        raise ValidationError("Branding file is not available.")
    if stored_file.file_type != expected_type:
        raise ValidationError("Invalid branding file type.")


def validate_logo_file(stored_file) -> None:
    validate_branding_file(stored_file, expected_type=StorageFileType.COLLEGE_LOGO)


def validate_banner_file(stored_file) -> None:
    validate_branding_file(stored_file, expected_type=StorageFileType.COLLEGE_LOGO)


def validate_campus_image_file(stored_file) -> None:
    if stored_file is None:
        raise ValidationError("Campus image not found.")
    if stored_file.is_deleted or stored_file.status != StorageFileStatus.ACTIVE:
        raise ValidationError("Campus image is not available.")
