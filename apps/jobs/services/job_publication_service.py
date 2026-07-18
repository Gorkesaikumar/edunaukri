from django.utils import timezone

from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import BusinessLogicException
from apps.core.services.base import BaseService
from apps.jobs.constants.enums import PUBLISHABLE_STATUSES, JobStatus
from apps.jobs.models import JobPosting
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.jobs.services.base import JobServiceBase
from apps.jobs.services.job_validation_service import JobValidationService


class JobPublicationService(JobServiceBase):
    """Publish / unpublish jobs and enforce the verified-company rule."""

    def __init__(self):
        super().__init__()
        self.job_repo = JobPostingRepository()
        self.validation = JobValidationService()

    @BaseService.atomic
    def publish(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status not in PUBLISHABLE_STATUSES:
            raise BusinessLogicException(
                "Only draft, pending or paused jobs can be published."
            )
        if not job_posting.company.can_publish_jobs:
            raise BusinessLogicException("Only verified companies may publish jobs.")
        self.validation.validate_can_publish(job_posting)

        job_posting = self.job_repo.update(
            job_posting,
            status=JobStatus.PUBLISHED,
            published_at=job_posting.published_at or timezone.now(),
            updated_by_id=recruiter.user_id,
        )
        self._audit(job_posting, "job.published", recruiter.user_id, {})
        self._trigger_recommendations(job_posting)
        return job_posting

    @BaseService.atomic
    def unpublish(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status != JobStatus.PUBLISHED:
            raise BusinessLogicException("Only published jobs can be unpublished.")
        job_posting = self.job_repo.update(
            job_posting, status=JobStatus.DRAFT, updated_by_id=recruiter.user_id
        )
        self._audit(job_posting, "job.unpublished", recruiter.user_id, {})
        return job_posting

    @staticmethod
    def _trigger_recommendations(job_posting: JobPosting) -> None:
        from apps.it_recruitment.services.job_recommendation_trigger_service import (
            JobRecommendationTriggerService,
        )

        JobRecommendationTriggerService().schedule_job_rebuild(
            job_posting.pk, reason="job_published"
        )

    @BaseService.atomic
    def admin_approve(
        self, *, job_posting: JobPosting, admin_id, remarks: str = ""
    ) -> JobPosting:
        """Admin approval: bypasses recruiter/company-verified checks."""
        job_posting = self.job_repo.update(
            job_posting,
            status=JobStatus.PUBLISHED,
            published_at=job_posting.published_at or timezone.now(),
            updated_by_id=admin_id,
        )
        self.audit.record(
            domain=DomainType.IT,
            event_type="job.approved",
            entity_type=EntityReferenceType.IT_JOB_POSTING,
            entity_id=job_posting.pk,
            payload={"status": JobStatus.PUBLISHED, "remarks": remarks},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        self._trigger_recommendations(job_posting)
        return job_posting

    @BaseService.atomic
    def admin_reject(
        self, *, job_posting: JobPosting, admin_id, remarks: str = ""
    ) -> JobPosting:
        """Admin rejection: moves job to REJECTED status."""
        job_posting = self.job_repo.update(
            job_posting,
            status=JobStatus.REJECTED,
            updated_by_id=admin_id,
        )
        self.audit.record(
            domain=DomainType.IT,
            event_type="job.rejected",
            entity_type=EntityReferenceType.IT_JOB_POSTING,
            entity_id=job_posting.pk,
            payload={"status": JobStatus.REJECTED, "remarks": remarks},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return job_posting
