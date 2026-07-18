from django.utils import timezone

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.applications.repositories.application_repository import (
    JobApplicationRepository,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.application_event_service import ApplicationEventService
from apps.applications.services.application_history_service import (
    ApplicationHistoryService,
)
from apps.applications.services.application_validation_service import (
    ApplicationValidationService,
)
from apps.applications.services.application_workflow_service import (
    ApplicationWorkflowService,
)
from apps.applications.services.base import ApplicationServiceBase
from apps.applications.workflow.engine import ApplicationWorkflowEngine
from apps.core.services.base import BaseService
from apps.jobs.models import JobPosting
from apps.jobs.repositories.job_repository import JobPostingRepository


class JobApplicationService(ApplicationServiceBase):
    """Create, withdraw, and delegate status changes for IT job applications."""

    def __init__(self):
        super().__init__()
        self.repository = JobApplicationRepository()
        self.job_repository = JobPostingRepository()
        self.validation = ApplicationValidationService()
        self.history = ApplicationHistoryService()
        self.workflow = ApplicationWorkflowService()
        self.authorization = ApplicationAuthorizationService()
        self.events = ApplicationEventService()

    @BaseService.atomic
    def apply(
        self,
        *,
        job_posting: JobPosting,
        job_seeker,
        cover_letter="",
        resume_file=None,
        expected_salary=None,
        notice_period="",
        current_location="",
        source="",
    ) -> JobApplication:
        self.validation.validate_job_open(job_posting)
        self.validation.validate_no_duplicate(
            exists=self.repository.exists(
                job_posting=job_posting, job_seeker=job_seeker
            )
        )

        from apps.core.services.config import get_setting
        from apps.core.exceptions.domain_exceptions import ValidationException

        max_apps = get_setting("limits.max_applications_per_job", {"count": 500}).get(
            "count", 500
        )
        current_apps = job_posting.applications.filter(is_deleted=False).count()
        if current_apps >= max_apps:
            raise ValidationException("Application limit has been reached.")

        self.validation.validate_apply_payload(
            {
                "expected_salary": expected_salary,
                "notice_period": notice_period,
                "source": source or "direct",
            }
        )

        resume = resume_file or job_seeker.resume_file
        self.validation.validate_resume_presence(resume)
        resume_snapshot = self._build_resume_snapshot(resume)

        application = self.repository.create(
            job_posting=job_posting,
            job_seeker=job_seeker,
            company=job_posting.company,
            resume_file=resume,
            resume_snapshot=resume_snapshot,
            cover_letter=cover_letter,
            expected_salary=expected_salary or job_seeker.expected_salary,
            notice_period=notice_period,
            current_location=current_location or job_seeker.current_location,
            source=source or "direct",
            status=ApplicationWorkflowEngine.initial_status(),
            applicant_name_snapshot=job_seeker.full_name,
            job_title_snapshot=job_posting.title,
            company_name_snapshot=job_posting.company_name_snapshot,
            created_by_id=job_seeker.user_id,
        )
        self.job_repository.increment_application_count(job_posting)
        self.history.record_status_change(
            application,
            from_status=None,
            to_status=application.status,
            notes="Application submitted.",
            actor_id=job_seeker.user_id,
        )
        self.events.record_it_applied(application)
        self._audit(
            application,
            "application.created",
            job_seeker.user_id,
            {"job_posting_id": str(job_posting.pk)},
        )
        return application

    @BaseService.atomic
    def update_status_for_actor(
        self,
        application: JobApplication,
        new_status: str,
        notes: str,
        *,
        actor,
        rejection_reason: str = "",
    ) -> JobApplication:
        return self.workflow.update_status_for_actor(
            application,
            new_status,
            notes,
            actor=actor,
            rejection_reason=rejection_reason,
        )

    @BaseService.atomic
    def withdraw(self, application: JobApplication, *, actor) -> JobApplication:
        return self.workflow.update_status_for_actor(
            application,
            JobApplicationStatus.WITHDRAWN,
            notes="Withdrawn by applicant.",
            actor=actor,
        )

    @BaseService.atomic
    def update_status(
        self,
        application: JobApplication,
        new_status: str,
        notes: str = "",
        *,
        rejection_reason: str = "",
    ) -> JobApplication:
        """Direct status update (used by billing/infra tests and internal callers)."""
        return self.workflow.update_status(
            application, new_status, notes, rejection_reason=rejection_reason
        )

    @BaseService.atomic
    def add_recruiter_notes(
        self, application: JobApplication, *, notes: str, actor
    ) -> JobApplication:
        self.authorization.ensure_can_update_it_status(
            application, application.status, actor
        )
        application.recruiter_notes = notes
        application.save(update_fields=["recruiter_notes", "updated_at"])
        self.history.record_comment(
            application,
            notes=notes,
            event_type="recruiter_comment",
            actor_id=getattr(actor, "pk", None),
        )
        return application

    @BaseService.atomic
    def add_internal_remarks(
        self, application: JobApplication, *, remarks: str, actor
    ) -> JobApplication:
        self.authorization.ensure_can_update_it_status(
            application, application.status, actor
        )
        application.internal_remarks = remarks
        application.save(update_fields=["internal_remarks", "updated_at"])
        self.history.record_comment(
            application,
            notes=remarks,
            event_type="recruiter_comment",
            actor_id=getattr(actor, "pk", None),
        )
        return application

    @BaseService.atomic
    def add_candidate_notes(
        self, application: JobApplication, *, notes: str, actor
    ) -> JobApplication:
        self.authorization.ensure_can_update_candidate_notes(application, actor)
        application.candidate_notes = notes
        application.save(update_fields=["candidate_notes", "updated_at"])
        return application

    @BaseService.atomic
    def soft_delete(self, application: JobApplication, *, actor) -> None:
        self.authorization.ensure_can_soft_delete_it_application(application, actor)
        application.deleted_by_id = getattr(actor, "pk", None)
        application.save(update_fields=["deleted_by_id"])
        self.repository.soft_delete(application)

    @staticmethod
    def _build_resume_snapshot(resume_file) -> dict:
        if not resume_file:
            return {}
        return {
            "file_id": str(resume_file.pk),
            "original_filename": resume_file.original_filename,
            "mime_type": resume_file.mime_type,
            "file_size_bytes": resume_file.file_size_bytes,
            "captured_at": timezone.now().isoformat(),
        }


# FacultyApplicationService lives in faculty_application_service.py.
