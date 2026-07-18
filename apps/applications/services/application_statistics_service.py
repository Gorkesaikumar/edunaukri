from django.db.models import Count

from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import JobApplication
from apps.applications.selectors.application_selector import (
    CandidateApplicationSelector,
    JobApplicationSelector,
    RecruiterApplicationSelector,
)


class ApplicationStatisticsService(BaseService):
    """Aggregated application statistics for seekers, recruiters, and admins."""

    def __init__(self):
        self.selector = JobApplicationSelector()
        self.recruiter_selector = RecruiterApplicationSelector()
        self.candidate_selector = CandidateApplicationSelector()

    def _summarize(self, queryset) -> dict:
        status_counts = dict(
            queryset.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        by_status = {
            choice.value: status_counts.get(choice.value, 0)
            for choice in JobApplicationStatus
        }
        terminal = (
            JobApplicationStatus.HIRED,
            JobApplicationStatus.REJECTED,
            JobApplicationStatus.WITHDRAWN,
            JobApplicationStatus.EXPIRED,
        )
        return {
            "total_applications": queryset.count(),
            "applications_by_status": by_status,
            "active_applications": queryset.exclude(status__in=terminal).count(),
        }

    def seeker_dashboard(self, job_seeker) -> dict:
        return self._summarize(self.candidate_selector.for_seeker(job_seeker))

    def recruiter_dashboard(self, recruiter) -> dict:
        return self._summarize(self.recruiter_selector.for_recruiter(recruiter))

    def company_dashboard(self, *, company_id, recruiter) -> dict:
        if not CompanyMemberSelector().is_member(recruiter, company_id):
            raise PermissionDeniedException("You are not a member of this company.")
        return self._summarize(self.selector.for_company(company_id))

    def platform_dashboard(self) -> dict:
        return self._summarize(self.selector.filter_by())

    def application_statistics(self, application: JobApplication) -> dict:
        return {
            "application_id": str(application.pk),
            "status": application.status,
            "applied_at": application.applied_at,
            "status_changed_at": application.status_changed_at,
            "hired_at": application.hired_at,
            "job_posting_id": str(application.job_posting_id),
            "company_id": str(application.company_id)
            if application.company_id
            else None,
        }
