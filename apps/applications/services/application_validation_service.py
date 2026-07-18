from django.core.exceptions import ValidationError

from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
    ResumeRequiredException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.validators.application_validators import (
    validate_application_source,
    validate_expected_salary,
    validate_job_accepts_applications,
    validate_not_terminal,
    validate_notice_period,
    validate_resume_presence,
    validate_withdraw_not_to_hired,
)
from apps.applications.workflow.engine import ApplicationWorkflowEngine


class ApplicationValidationService(BaseService):
    """Centralized validation for job application payloads and transitions."""

    def validate_apply_payload(self, data: dict) -> None:
        try:
            if "expected_salary" in data:
                validate_expected_salary(data.get("expected_salary"))
            if "notice_period" in data:
                validate_notice_period(data.get("notice_period", ""))
            if "source" in data:
                validate_application_source(data.get("source"))
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Invalid application data."
            ) from exc

    def validate_job_open(self, job_posting) -> None:
        try:
            validate_job_accepts_applications(job_posting)
        except ValidationError as exc:
            raise ValidationException(
                exc.messages[0] if exc.messages else "Job not open."
            ) from exc

    def validate_resume_presence(self, resume_file) -> None:
        try:
            validate_resume_presence(resume_file)
        except ValidationError as exc:
            raise ResumeRequiredException(
                exc.messages[0]
                if exc.messages
                else "A valid resume is required to apply for this job."
            ) from exc

    def validate_transition(self, application, new_status: str) -> None:
        try:
            validate_not_terminal(application)
            validate_withdraw_not_to_hired(application.status, new_status)
            ApplicationWorkflowEngine.validate_transition(
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
            raise ConflictException("You have already applied to this job.")

    def normalize_status(self, status: str) -> str:
        return ApplicationWorkflowEngine.normalize_status(status)
