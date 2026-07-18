"""Centralized validation for faculty vacancy payloads."""

from django.core.exceptions import ValidationError

from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.faculty.validators.vacancy_validators import (
    validate_application_deadline,
    validate_designation,
    validate_employment_type,
    validate_experience_range,
    validate_qualification,
    validate_salary_range,
    validate_specialization,
    validate_vacancy_count,
    validate_work_type,
)


class FacultyValidationService(BaseService):
    """Single entry point for validating a vacancy create/update payload."""

    def validate_payload(self, data: dict, *, partial: bool = False) -> None:
        try:
            if not partial:
                if not data.get("title"):
                    raise ValidationError("Vacancy title is required.")
                if not data.get("description"):
                    raise ValidationError("Vacancy description is required.")

            if "employment_type" in data:
                validate_employment_type(data.get("employment_type"))
            if "work_type" in data:
                validate_work_type(data.get("work_type"))
            if "designation" in data:
                validate_designation(data.get("designation"))
            for key in ("minimum_qualification", "preferred_qualification"):
                if key in data:
                    validate_qualification(data.get(key))
            if "specialization_required" in data:
                validate_specialization(data.get("specialization_required"))
            if "salary_min" in data or "salary_max" in data:
                validate_salary_range(data.get("salary_min"), data.get("salary_max"))
            if "experience_min" in data or "experience_max" in data:
                validate_experience_range(
                    data.get("experience_min"), data.get("experience_max")
                )
            if "vacancy_count" in data:
                validate_vacancy_count(data.get("vacancy_count"))
            if "application_deadline" in data or "expires_at" in data:
                validate_application_deadline(
                    data.get("application_deadline"), data.get("expires_at")
                )
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid vacancy data."
            ) from exc

    def validate_can_publish(self, vacancy) -> None:
        try:
            if not vacancy.title or not vacancy.description:
                raise ValidationError(
                    "Vacancy must have a title and description before publishing."
                )
            validate_vacancy_count(vacancy.vacancy_count)
            validate_application_deadline(
                vacancy.application_deadline, vacancy.expires_at
            )
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Vacancy cannot be published."
            ) from exc
