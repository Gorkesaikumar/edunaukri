"""Field-level validators for the Job Application Management module."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.applications.constants.enums import ApplicationSource, JobApplicationStatus
from apps.applications.workflow.engine import ApplicationWorkflowEngine
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting


def validate_expected_salary(value) -> None:
    if value is not None and Decimal(value) < 0:
        raise ValidationError("Expected salary cannot be negative.")


def validate_notice_period(value: str) -> None:
    if value and len(value) > 100:
        raise ValidationError("Notice period is too long.")


def validate_application_source(value) -> None:
    if value and value not in ApplicationSource.values:
        raise ValidationError("Invalid application source.")


def validate_status_transition(from_status: str | None, to_status: str) -> None:
    ApplicationWorkflowEngine.validate_transition(from_status, to_status)


def validate_job_accepts_applications(job_posting: JobPosting) -> None:
    if job_posting.status != JobStatus.PUBLISHED:
        raise ValidationError("Job is not open for applications.")
    if job_posting.status in (JobStatus.CLOSED, JobStatus.EXPIRED, JobStatus.ARCHIVED):
        raise ValidationError("Job is closed and cannot receive applications.")
    now = timezone.now()
    if job_posting.expires_at and job_posting.expires_at <= now:
        raise ValidationError("Job has expired and cannot receive applications.")


def validate_not_terminal(application) -> None:
    if ApplicationWorkflowEngine.is_terminal(application.status):
        raise ValidationError("Applications in a terminal status cannot be modified.")


def validate_withdraw_not_to_hired(from_status: str, to_status: str) -> None:
    normalized_from = ApplicationWorkflowEngine.normalize_status(from_status)
    normalized_to = ApplicationWorkflowEngine.normalize_status(to_status)
    if (
        normalized_from == JobApplicationStatus.WITHDRAWN
        and normalized_to == JobApplicationStatus.HIRED
    ):
        raise ValidationError("Withdrawn applications cannot be hired.")


def validate_resume_presence(resume_file) -> None:
    from apps.core.exceptions.domain_exceptions import ResumeRequiredException

    if not resume_file:
        raise ResumeRequiredException(
            "A valid resume is required to apply for this job."
        )

    from apps.documents.constants.enums import StorageFileStatus, StorageFileType

    if resume_file.status != StorageFileStatus.ACTIVE:
        raise ResumeRequiredException(
            "The attached resume file is no longer available."
        )

    if resume_file.file_type not in (StorageFileType.RESUME, StorageFileType.CV):
        raise ResumeRequiredException(
            "The attached file must be a valid resume document."
        )
