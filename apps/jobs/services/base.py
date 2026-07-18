"""Shared base for Job Management services."""

from apps.audit.services.audit_service import AuditService
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.constants.enums import ActorType, DomainType, EntityReferenceType
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.jobs.models import JobPosting


class JobServiceBase(BaseService):
    """Common ownership guard + audit helper for job services."""

    def __init__(self):
        self.member_selector = CompanyMemberSelector()
        self.audit = AuditService()

    def _ensure_manages_job(self, job_posting: JobPosting, recruiter) -> None:
        if not self.member_selector.is_member(recruiter, job_posting.company_id):
            raise PermissionDeniedException("You do not manage this job posting.")

    def _audit(
        self, job_posting: JobPosting, event_type: str, actor_id, payload: dict
    ) -> None:
        self.audit.record(
            domain=DomainType.IT,
            event_type=event_type,
            entity_type=EntityReferenceType.IT_JOB_POSTING,
            entity_id=job_posting.pk,
            payload=payload,
            actor_type=ActorType.IT_USER,
            actor_id=actor_id,
        )
