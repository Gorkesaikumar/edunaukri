from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    ResumeRequiredException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.applications.validators.faculty_application_validators import (
    validate_cv_presence,
    validate_faculty_application_source,
    validate_faculty_expected_salary,
    validate_faculty_not_terminal,
    validate_vacancy_accepts_applications,
    validate_withdraw_not_to_joined,
)
from apps.applications.workflow.faculty_engine import FacultyApplicationWorkflowEngine
from django.core.exceptions import ValidationError


class FacultyApplicationValidationService(BaseService):
    """Centralized validation for faculty application payloads and transitions."""

    def validate_apply_payload(self, data: dict) -> None:
        try:
            if "expected_salary" in data:
                validate_faculty_expected_salary(data.get("expected_salary"))
            if "source" in data:
                validate_faculty_application_source(data.get("source"))
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid application data."
            ) from exc

    def validate_vacancy_open(self, vacancy) -> None:
        try:
            validate_vacancy_accepts_applications(vacancy)
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Vacancy not open."
            ) from exc

    def validate_cv_presence(self, cv_file) -> None:
        try:
            validate_cv_presence(cv_file)
        except ValidationError as exc:
            raise ResumeRequiredException(
                exc.messages[0]
                if exc.messages
                else "A valid CV is required to apply for this vacancy."
            ) from exc

    def validate_transition(self, application, new_status: str) -> None:
        try:
            validate_faculty_not_terminal(application)
            validate_withdraw_not_to_joined(application.status, new_status)
            FacultyApplicationWorkflowEngine.validate_transition(
                application.status, new_status
            )
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid transition."
            ) from exc
        except BusinessLogicException:
            raise

    def validate_no_duplicate(self, *, exists: bool) -> None:
        if exists:
            raise ConflictException("You have already applied to this vacancy.")

    def normalize_status(self, status: str) -> str:
        return FacultyApplicationWorkflowEngine.normalize_status(status)
