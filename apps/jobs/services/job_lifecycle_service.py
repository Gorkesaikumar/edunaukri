from django.utils import timezone

from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import BusinessLogicException
from apps.core.services.base import BaseService
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.jobs.services.base import JobServiceBase


class JobLifecycleService(JobServiceBase):
    """Status transitions for job postings: pause, reopen, close, archive, expire."""

    def __init__(self):
        super().__init__()
        self.job_repo = JobPostingRepository()

    @BaseService.atomic
    def pause(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status != JobStatus.PUBLISHED:
            raise BusinessLogicException("Only published jobs can be paused.")
        return self._transition(
            job_posting, JobStatus.PAUSED, recruiter.user_id, "job.paused"
        )

    @BaseService.atomic
    def reopen(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status not in (JobStatus.PAUSED, JobStatus.CLOSED):
            raise BusinessLogicException("Only paused or closed jobs can be reopened.")
        if not job_posting.company.can_publish_jobs:
            raise BusinessLogicException("Only verified companies may reopen jobs.")
        job_posting = self.job_repo.update(
            job_posting,
            status=JobStatus.PUBLISHED,
            closed_at=None,
            published_at=job_posting.published_at or timezone.now(),
            updated_by_id=recruiter.user_id,
        )
        self._audit(job_posting, "job.reopened", recruiter.user_id, {})
        return job_posting

    @BaseService.atomic
    def close(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status not in (
            JobStatus.DRAFT,
            JobStatus.PUBLISHED,
            JobStatus.PAUSED,
            JobStatus.PENDING_APPROVAL,
        ):
            raise BusinessLogicException(
                "Job cannot be closed from its current status."
            )
        job_posting = self.job_repo.update(
            job_posting,
            status=JobStatus.CLOSED,
            closed_at=timezone.now(),
            updated_by_id=recruiter.user_id,
        )
        self._audit(job_posting, "job.closed", recruiter.user_id, {})
        return job_posting

    @BaseService.atomic
    def archive(self, *, job_posting: JobPosting, recruiter) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if job_posting.status == JobStatus.ARCHIVED:
            return job_posting
        return self._transition(
            job_posting, JobStatus.ARCHIVED, recruiter.user_id, "job.archived"
        )

    @BaseService.atomic
    def expire(self, *, job_posting: JobPosting, actor_id=None) -> JobPosting:
        """Mark a published job as expired (used by scheduled expiry sweeps)."""
        if job_posting.status != JobStatus.PUBLISHED:
            raise BusinessLogicException("Only published jobs can expire.")
        return self._transition(job_posting, JobStatus.EXPIRED, actor_id, "job.expired")

    @BaseService.atomic
    def admin_close(self, *, job_posting: JobPosting, admin_id) -> JobPosting:
        if job_posting.status not in (
            JobStatus.DRAFT,
            JobStatus.PUBLISHED,
            JobStatus.PAUSED,
            JobStatus.PENDING_APPROVAL,
        ):
            raise BusinessLogicException(
                "Job cannot be closed from its current status."
            )
        job_posting = self.job_repo.update(
            job_posting,
            status=JobStatus.CLOSED,
            closed_at=timezone.now(),
            updated_by_id=admin_id,
        )
        self.audit.record(
            domain=DomainType.IT,
            event_type="job.closed",
            entity_type=EntityReferenceType.IT_JOB_POSTING,
            entity_id=job_posting.pk,
            payload={"status": JobStatus.CLOSED},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return job_posting

    @BaseService.atomic
    def admin_archive(self, *, job_posting: JobPosting, admin_id) -> JobPosting:
        if job_posting.status == JobStatus.ARCHIVED:
            return job_posting
        job_posting = self.job_repo.update(
            job_posting, status=JobStatus.ARCHIVED, updated_by_id=admin_id
        )
        self.audit.record(
            domain=DomainType.IT,
            event_type="job.archived",
            entity_type=EntityReferenceType.IT_JOB_POSTING,
            entity_id=job_posting.pk,
            payload={"status": JobStatus.ARCHIVED},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return job_posting

    def _transition(
        self, job_posting: JobPosting, status: str, actor_id, event_type: str
    ) -> JobPosting:
        job_posting = self.job_repo.update(
            job_posting, status=status, updated_by_id=actor_id
        )
        self._audit(job_posting, event_type, actor_id, {"status": status})
        return job_posting
