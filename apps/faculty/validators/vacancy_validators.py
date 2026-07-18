"""Field-level validators for the Faculty Vacancy Management module."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.faculty.constants.enums import (
    Designation,
    EmploymentType,
    QualificationLevel,
    WorkType,
)


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


def validate_vacancy_count(value) -> None:
    if value is None:
        return
    if int(value) < 1:
        raise ValidationError("A vacancy must have at least one position.")
    if int(value) > 100000:
        raise ValidationError("Vacancy count is unrealistically high.")


def validate_employment_type(value) -> None:
    if value and value not in EmploymentType.values:
        raise ValidationError("Invalid employment type.")


def validate_work_type(value) -> None:
    if value and value not in WorkType.values:
        raise ValidationError("Invalid work type.")


def validate_designation(value) -> None:
    if value and value not in Designation.values:
        raise ValidationError("Invalid designation.")


def validate_qualification(value) -> None:
    if value and value not in QualificationLevel.values:
        raise ValidationError("Invalid qualification level.")


def validate_specialization(value) -> None:
    if value is None:
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            if not str(item).strip():
                raise ValidationError("Specialization entries cannot be blank.")
    elif not str(value).strip():
        raise ValidationError("Specialization cannot be blank.")


def validate_application_deadline(deadline, expires_at=None) -> None:
    now = timezone.now()
    if deadline is not None and deadline <= now:
        raise ValidationError("Application deadline must be in the future.")
    if expires_at is not None and expires_at <= now:
        raise ValidationError("Expiry date must be in the future.")
    if deadline is not None and expires_at is not None and deadline > expires_at:
        raise ValidationError("Application deadline cannot be after the expiry date.")
