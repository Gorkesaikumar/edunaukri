"""Field-level validators for the Faculty Application Management module."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.applications.constants.enums import ApplicationSource
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.workflow.faculty_engine import FacultyApplicationWorkflowEngine
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy


def validate_faculty_expected_salary(value) -> None:
    if value is not None and Decimal(value) < 0:
        raise ValidationError("Expected salary cannot be negative.")


def validate_faculty_application_source(value) -> None:
    if value and value not in ApplicationSource.values:
        raise ValidationError("Invalid application source.")


def validate_faculty_status_transition(from_status: str | None, to_status: str) -> None:
    FacultyApplicationWorkflowEngine.validate_transition(from_status, to_status)


def validate_vacancy_accepts_applications(vacancy: FacultyVacancy) -> None:
    if vacancy.status != VacancyStatus.PUBLISHED:
        raise ValidationError("Vacancy is not open for applications.")
    if vacancy.status in (
        VacancyStatus.CLOSED,
        VacancyStatus.EXPIRED,
        VacancyStatus.ARCHIVED,
    ):
        raise ValidationError("Vacancy is closed and cannot receive applications.")
    now = timezone.now()
    if vacancy.expires_at and vacancy.expires_at <= now:
        raise ValidationError("Vacancy has expired and cannot receive applications.")
    if vacancy.application_deadline and vacancy.application_deadline <= now:
        raise ValidationError("Application deadline has passed for this vacancy.")


def validate_faculty_not_terminal(application) -> None:
    if FacultyApplicationWorkflowEngine.is_terminal(application.status):
        raise ValidationError("Applications in a terminal status cannot be modified.")


def validate_withdraw_not_to_joined(from_status: str, to_status: str) -> None:
    normalized_from = FacultyApplicationWorkflowEngine.normalize_status(from_status)
    normalized_to = FacultyApplicationWorkflowEngine.normalize_status(to_status)
    if (
        normalized_from == FacultyApplicationStatus.WITHDRAWN
        and normalized_to == FacultyApplicationStatus.JOINED
    ):
        raise ValidationError("Withdrawn applications cannot be joined.")


def validate_cv_presence(cv_file) -> None:
    from apps.core.exceptions.domain_exceptions import ResumeRequiredException

    if not cv_file:
        raise ResumeRequiredException(
            "A valid CV is required to apply for this vacancy."
        )

    from apps.documents.constants.enums import StorageFileStatus, StorageFileType

    if cv_file.status != StorageFileStatus.ACTIVE:
        raise ResumeRequiredException("The attached CV file is no longer available.")

    if cv_file.file_type not in (StorageFileType.RESUME, StorageFileType.CV):
        raise ResumeRequiredException("The attached file must be a valid CV document.")
