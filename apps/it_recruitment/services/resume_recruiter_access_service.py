"""Recruiter resume access with analytics and candidate notifications."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied

from apps.applications.models import JobApplication
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.documents.models import StoredFile
from apps.it_recruitment.services.resume_analytics_service import ResumeAnalyticsService
from apps.notifications.services.outbox_processor import OutboxProcessorService


class ResumeRecruiterAccessService(BaseService):
    def resolve_application_resume(
        self, application: JobApplication, *, actor
    ) -> StoredFile:
        ApplicationAuthorizationService().ensure_can_view_it_application(
            application, actor
        )
        from apps.it_recruitment.selectors.profile_selector import (
            JobSeekerProfileSelector,
        )
        from apps.it_recruitment.services.jobseeker_privacy_service import (
            JobSeekerPrivacyService,
        )

        seeker = JobSeekerProfileSelector().for_user(actor)
        if not seeker or seeker.pk != application.job_seeker_id:
            JobSeekerPrivacyService().ensure_can_download_resume(
                application.job_seeker, actor, application=application
            )
        from apps.documents.services.storage_service import StorageService

        stored = None
        if application.resume_file_id and getattr(application, "resume_file", None):
            f = application.resume_file
            if getattr(f, "status", None) == "active" and not getattr(f, "is_deleted", False):
                if StorageService().get_absolute_path(f).is_file():
                    stored = f

        if not stored and getattr(application, "job_seeker", None) and getattr(application.job_seeker, "resume_file", None):
            f = application.job_seeker.resume_file
            if getattr(f, "status", None) == "active" and not getattr(f, "is_deleted", False):
                if StorageService().get_absolute_path(f).is_file():
                    stored = f
                    try:
                        application.resume_file = stored
                        application.save(update_fields=["resume_file"])
                    except Exception:
                        pass

        if not stored:
            stored = application.resume_file or getattr(application, "job_seeker", None) and getattr(application.job_seeker, "resume_file", None)
        if not stored:
            raise PermissionDenied("Resume not available for this application.")
        return stored

    def record_recruiter_view(self, application: JobApplication, *, actor) -> None:
        stored = self.resolve_application_resume(application, actor=actor)
        self._increment_analytics(stored, key="views")
        self._notify_candidate(
            application,
            event_type="resume.viewed",
            title="Recruiter viewed your resume",
            body=f"A recruiter viewed your resume for {application.job_title_snapshot}.",
        )

    def record_recruiter_download(self, application: JobApplication, *, actor) -> None:
        stored = self.resolve_application_resume(application, actor=actor)
        ResumeAnalyticsService().record_recruiter_download(stored)
        recruiter_name = getattr(actor, "full_name", None) or "A recruiter"
        self._notify_candidate(
            application,
            event_type="resume_downloaded",
            title="Recruiter downloaded your resume",
            body=f"{recruiter_name} downloaded your resume for {application.job_title_snapshot}.",
        )

    @staticmethod
    def _increment_analytics(stored: StoredFile, *, key: str) -> None:
        from django.utils import timezone

        data = dict(stored.parsed_data or {})
        analytics = dict(data.get("analytics") or {})
        analytics[key] = int(analytics.get(key) or 0) + 1
        if key == "views":
            analytics["last_viewed_at"] = timezone.now().isoformat()
        data["analytics"] = analytics
        stored.parsed_data = data
        stored.save(update_fields=["parsed_data", "updated_at"])

    @staticmethod
    def _notify_candidate(
        application: JobApplication, *, event_type: str, title: str, body: str
    ) -> None:
        OutboxService().publish(
            domain=DomainType.IT,
            event_type=event_type,
            aggregate_type="it_job_application",
            aggregate_id=application.pk,
            payload={
                "recipient_domain": "it",
                "recipient_id": str(application.job_seeker.user_id),
                "title": title,
                "body": body,
            },
        )
        try:
            OutboxProcessorService().process_batch(limit=5)
        except Exception:
            pass
