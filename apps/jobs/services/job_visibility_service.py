from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.jobs.constants.enums import JobStatus, JobVisibility
from apps.jobs.models import JobPosting
from apps.jobs.repositories.job_repository import JobPostingRepository
from apps.jobs.services.base import JobServiceBase


class JobVisibilityService(JobServiceBase):
    """Featured / urgent flags, visibility scope, and public-visibility rules."""

    def __init__(self):
        super().__init__()
        self.job_repo = JobPostingRepository()

    @BaseService.atomic
    def set_featured(
        self, *, job_posting: JobPosting, recruiter, value: bool
    ) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        job_posting = self.job_repo.update(
            job_posting, is_featured=bool(value), updated_by_id=recruiter.user_id
        )
        self._audit(
            job_posting,
            "job.featured_changed",
            recruiter.user_id,
            {"is_featured": bool(value)},
        )
        return job_posting

    @BaseService.atomic
    def set_urgent(
        self, *, job_posting: JobPosting, recruiter, value: bool
    ) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        job_posting = self.job_repo.update(
            job_posting, is_urgent=bool(value), updated_by_id=recruiter.user_id
        )
        self._audit(
            job_posting,
            "job.urgent_changed",
            recruiter.user_id,
            {"is_urgent": bool(value)},
        )
        return job_posting

    @BaseService.atomic
    def set_visibility(
        self, *, job_posting: JobPosting, recruiter, visibility: str
    ) -> JobPosting:
        self._ensure_manages_job(job_posting, recruiter)
        if visibility not in JobVisibility.values:
            raise ValidationException("Invalid visibility value.")
        job_posting = self.job_repo.update(
            job_posting, visibility=visibility, updated_by_id=recruiter.user_id
        )
        self._audit(
            job_posting,
            "job.visibility_changed",
            recruiter.user_id,
            {"visibility": visibility},
        )
        return job_posting

    @BaseService.atomic
    def admin_set_featured(
        self, *, job_posting: JobPosting, admin_id, value: bool
    ) -> JobPosting:
        job_posting = self.job_repo.update(
            job_posting, is_featured=bool(value), updated_by_id=admin_id
        )
        self.audit.record(
            domain=DomainType.IT,
            event_type="job.featured_changed",
            entity_type=EntityReferenceType.IT_JOB_POSTING,
            entity_id=job_posting.pk,
            payload={"is_featured": bool(value)},
            actor_type=ActorType.ADMIN,
            actor_id=admin_id,
        )
        return job_posting

    @staticmethod
    def is_publicly_visible(job_posting: JobPosting) -> bool:
        return (
            job_posting.status == JobStatus.PUBLISHED
            and job_posting.visibility == JobVisibility.PUBLIC
            and not job_posting.is_deleted
        )
