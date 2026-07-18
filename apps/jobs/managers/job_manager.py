"""Model managers for the Job Management module."""

from apps.core.managers import ActiveManager, SoftDeleteQuerySet
from apps.jobs.constants.enums import JobStatus


class JobPostingQuerySet(SoftDeleteQuerySet):
    def published(self):
        return self.filter(status=JobStatus.PUBLISHED)

    def drafts(self):
        return self.filter(status=JobStatus.DRAFT)

    def live(self):
        """Published jobs that have not expired or been closed/archived."""
        return self.filter(status=JobStatus.PUBLISHED)

    def featured(self):
        return self.filter(status=JobStatus.PUBLISHED, is_featured=True)

    def urgent(self):
        return self.filter(status=JobStatus.PUBLISHED, is_urgent=True)

    def for_company(self, company_id):
        return self.filter(company_id=company_id)


class JobPostingManager(ActiveManager.from_queryset(JobPostingQuerySet)):
    """Default manager returning only non-deleted job postings with domain scopes."""
