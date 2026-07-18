"""Field-level validators for the Job Management module."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.jobs.constants.enums import EmploymentType, WorkMode


def validate_salary_range(salary_min, salary_max) -> None:
    for value, label in (
        (salary_min, "Minimum salary"),
        (salary_max, "Maximum salary"),
    ):
        if value is not None and Decimal(value) < 0:
            raise ValidationError(f"{label} cannot be negative.")
    if (
        salary_min is not None
        and salary_max is not None
        and Decimal(salary_min) > Decimal(salary_max)
    ):
        raise ValidationError("Minimum salary cannot exceed maximum salary.")


def validate_experience_range(experience_min, experience_max) -> None:
    for value, label in (
        (experience_min, "Minimum experience"),
        (experience_max, "Maximum experience"),
    ):
        if value is not None and int(value) < 0:
            raise ValidationError(f"{label} cannot be negative.")
        if value is not None and int(value) > 60:
            raise ValidationError(f"{label} is unrealistically high.")
    if (
        experience_min is not None
        and experience_max is not None
        and int(experience_min) > int(experience_max)
    ):
        raise ValidationError("Minimum experience cannot exceed maximum experience.")


def validate_vacancies(value) -> None:
    if value is None:
        return
    if int(value) < 1:
        raise ValidationError("A job must have at least one vacancy.")
    if int(value) > 100000:
        raise ValidationError("Vacancy count is unrealistically high.")


def validate_employment_type(value) -> None:
    if value and value not in EmploymentType.values:
        raise ValidationError("Invalid employment type.")


def validate_work_mode(value) -> None:
    if value and value not in WorkMode.values:
        raise ValidationError("Invalid work mode.")


def validate_skills(value) -> None:
    if value is None:
        return
    if not isinstance(value, (list, tuple)):
        raise ValidationError("Skills must be provided as a list.")
    for item in value:
        if not str(item).strip():
            raise ValidationError("Skill names cannot be blank.")


def validate_application_deadline(deadline, expires_at=None) -> None:
    now = timezone.now()
    if deadline is not None and deadline <= now:
        raise ValidationError("Application deadline must be in the future.")
    if expires_at is not None and expires_at <= now:
        raise ValidationError("Expiry date must be in the future.")
    if deadline is not None and expires_at is not None and deadline > expires_at:
        raise ValidationError("Application deadline cannot be after the expiry date.")


def validate_location(*, work_mode, city="", country="") -> None:
    """Onsite / hybrid roles must declare a physical location."""
    if work_mode in (WorkMode.ONSITE, WorkMode.HYBRID) and not (city or country):
        raise ValidationError("Onsite or hybrid jobs must specify a city or country.")
