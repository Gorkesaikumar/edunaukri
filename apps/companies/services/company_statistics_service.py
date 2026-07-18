from apps.companies.models import Company
from apps.companies.selectors.company_selector import (
    CompanyDashboardSelector,
    CompanyLocationSelector,
    CompanyMemberSelector,
)
from apps.core.services.base import BaseService


class CompanyStatisticsService(BaseService):
    """Aggregated, read-only statistics for companies and recruiter dashboards."""

    def __init__(self):
        self.dashboard_selector = CompanyDashboardSelector()
        self.member_selector = CompanyMemberSelector()
        self.location_selector = CompanyLocationSelector()

    def recruiter_dashboard(self, recruiter) -> dict:
        return self.dashboard_selector.summary_for_recruiter(recruiter)

    def platform_dashboard(self) -> dict:
        return self.dashboard_selector.platform_summary()

    def company_statistics(self, company: Company) -> dict:
        return {
            "company_id": str(company.pk),
            "name": company.name,
            "verification_status": company.verification_status,
            "is_active": company.is_active,
            "member_count": self.member_selector.for_company(company.pk).count(),
            "location_count": self.location_selector.for_company(company.pk).count(),
            "job_count": self._job_count(company),
        }

    def _job_count(self, company: Company) -> int:
        try:
            from apps.jobs.selectors.job_selector import JobPostingSelector

            return JobPostingSelector().filter_by(company_id=company.pk).count()
        except Exception:  # noqa: BLE001 - jobs module optional for statistics
            return 0
