import re
from decimal import Decimal

from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.validators.common import validate_email, validate_phone, validate_url


def validate_experience_years(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        years = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationException(
            "Experience years must be a non-negative integer."
        ) from exc
    if years < 0 or years > 60:
        raise ValidationException("Experience years must be between 0 and 60.")
    return years


def validate_salary(value, *, field_name: str = "salary") -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        amount = Decimal(str(value))
    except Exception as exc:
        raise ValidationException(
            f"{field_name} must be a valid decimal amount."
        ) from exc
    if amount < 0:
        raise ValidationException(f"{field_name} cannot be negative.")
    return amount


def validate_notice_period_days(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationException(
            "Notice period must be a non-negative integer."
        ) from exc
    if days < 0 or days > 365:
        raise ValidationException("Notice period must be between 0 and 365 days.")
    return days


def validate_qualification_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        raise ValidationException("Qualification name is required.")
    if len(name) > 200:
        raise ValidationException("Qualification name is too long.")
    return name


def validate_profile_email(value: str) -> str:
    validate_email(value)
    return value.strip()


def validate_profile_phone(value: str) -> str:
    validate_phone(value)
    return re.sub(r"\D", "", value or "")


def validate_profile_url(value: str) -> str:
    validate_url(value)
    return value.strip()


def validate_file_reference_id(value):
    if value is None or value == "":
        return None
    return str(value)
