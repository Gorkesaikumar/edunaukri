"""Centralized validation for job payloads."""

from django.core.exceptions import ValidationError

from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.jobs.validators.job_validators import (
    validate_application_deadline,
    validate_employment_type,
    validate_experience_range,
    validate_location,
    validate_salary_range,
    validate_skills,
    validate_vacancies,
    validate_work_mode,
)


class JobValidationService(BaseService):
    """Single entry point for validating a job create/update payload."""

    def validate_payload(self, data: dict, *, partial: bool = False) -> None:
        try:
            if not partial:
                if not data.get("title"):
                    raise ValidationError("Job title is required.")
                if not data.get("description"):
                    raise ValidationError("Job description is required.")

            if "employment_type" in data:
                validate_employment_type(data.get("employment_type"))
            if "work_mode" in data:
                validate_work_mode(data.get("work_mode"))
            if "salary_min" in data or "salary_max" in data:
                validate_salary_range(data.get("salary_min"), data.get("salary_max"))
            if "experience_min" in data or "experience_max" in data:
                validate_experience_range(
                    data.get("experience_min"), data.get("experience_max")
                )
            if "vacancies" in data:
                validate_vacancies(data.get("vacancies"))
            if "application_deadline" in data or "expires_at" in data:
                validate_application_deadline(
                    data.get("application_deadline"), data.get("expires_at")
                )
            for key in ("required_skills", "preferred_skills"):
                if key in data:
                    validate_skills(data.get(key))
            if data.get("work_mode"):
                validate_location(
                    work_mode=data.get("work_mode"),
                    city=data.get("city", ""),
                    country=data.get("country", ""),
                )
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid job data."
            ) from exc

    def validate_can_publish(self, job_posting) -> None:
        try:
            if not job_posting.title or not job_posting.description:
                raise ValidationError(
                    "Job must have a title and description before publishing."
                )
            validate_vacancies(job_posting.vacancies)
            validate_application_deadline(
                job_posting.application_deadline, job_posting.expires_at
            )
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Job cannot be published."
            ) from exc
