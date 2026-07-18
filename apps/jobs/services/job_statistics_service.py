from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.jobs.models import JobPosting
from apps.jobs.selectors.job_dashboard import JobDashboardSelector


class JobStatisticsService(BaseService):
    """Aggregated, read-only job statistics for recruiters, companies and admins."""

    def __init__(self):
        self.dashboard = JobDashboardSelector()
        self.member_selector = CompanyMemberSelector()

    def recruiter_dashboard(self, recruiter) -> dict:
        return self.dashboard.recruiter_summary(recruiter)

    def company_dashboard(self, *, company_id, recruiter) -> dict:
        if not self.member_selector.is_member(recruiter, company_id):
            raise PermissionDeniedException("You are not a member of this company.")
        return self.dashboard.company_summary(company_id)

    def platform_dashboard(self) -> dict:
        return self.dashboard.platform_summary()

    def job_statistics(self, *, job_posting: JobPosting, recruiter) -> dict:
        if not self.member_selector.is_member(recruiter, job_posting.company_id):
            raise PermissionDeniedException("You do not manage this job posting.")
        return self.dashboard.job_statistics(job_posting)
