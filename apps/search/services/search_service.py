from django.core.exceptions import PermissionDenied, ValidationError

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.applications.selectors.application_selector import (
    ApplicationSearchSelector,
    FacultyApplicationSearchSelector,
)
from apps.core.services.base import BaseService
from apps.faculty.selectors.vacancy_search import VacancySearchSelector
from apps.invoices.selectors.invoice_selector import InvoiceSelector
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector
from apps.jobs.selectors.job_search import JobSearchSelector
from apps.search.constants.enums import SearchResource
from apps.search.selectors.global_search_selector import GlobalSearchSelector
from apps.search.selectors.registry_selectors import (
    CollegeSearchSelector,
    CompanySearchSelector,
    GuaranteeSearchSelector,
    JobSeekerSearchSelector,
    ProfessorSearchSelector,
    RecruiterSearchSelector,
)
from apps.search.services.filter_service import FilterService


class SearchService(BaseService):
    """Orchestrates domain and registry search selectors — no cross-domain coupling in selectors."""

    def __init__(self):
        self.filters = FilterService()

    def execute(self, resource: str, *, query_params, user=None):
        params = self.filters.parse(resource, query_params)
        if resource in (SearchResource.JOBS,):
            return self.search_jobs(**self.filters.map_jobs_params(params))
        if resource in (SearchResource.FACULTY, SearchResource.VACANCIES):
            return self.search_vacancies(**self.filters.map_faculty_params(params))
        if resource == SearchResource.COMPANIES:
            return CompanySearchSelector().search(
                **params, public_only=self._is_public(user)
            )
        if resource == SearchResource.COLLEGES:
            return CollegeSearchSelector().search(
                **params, public_only=self._is_public(user)
            )
        if resource == SearchResource.APPLICATIONS:
            return self.search_applications(
                user=user, **self.filters.map_applications_params(params)
            )
        if resource == SearchResource.INVOICES:
            return self._search_invoices(
                user=user, **self.filters.map_invoices_params(params)
            )
        if resource == SearchResource.GUARANTEES:
            return self._search_guarantees(user=user, **params)
        if resource == SearchResource.JOB_SEEKERS:
            return self._search_job_seekers(user=user, **params)
        if resource == SearchResource.RECRUITERS:
            return self._search_recruiters(user=user, **params)
        if resource == SearchResource.PROFESSORS:
            return self._search_professors(user=user, **params)
        if resource == SearchResource.ADMIN:
            return self._search_admin(user=user, **params)
        raise ValidationError(f"Unsupported search resource: {resource}")

    def search_jobs(self, **filters):
        return JobSearchSelector().search(**filters)

    def search_vacancies(self, **filters):
        return VacancySearchSelector().search(**filters)

    def search_applications(self, *, user=None, **params):
        domain = params.pop("domain", "") or "it"
        if domain == "faculty":
            college_user = user if isinstance(user, CollegeUser) else None
            return FacultyApplicationSearchSelector().search(
                query=params.get("query", ""),
                status=params.get("status", ""),
                college_id=params.get("college_id"),
                vacancy_id=params.get("vacancy_id"),
                college_user=college_user,
                sort=params.get("sort", "recent"),
            )
        recruiter = None
        if isinstance(user, ITUser):
            recruiter = RecruiterProfileSelector().for_user(user)
        return ApplicationSearchSelector().search(
            query=params.get("query", ""),
            status=params.get("status", ""),
            company_id=params.get("company_id"),
            job_posting_id=params.get("job_posting_id"),
            recruiter=recruiter,
            sort=params.get("sort", "recent"),
        )

    def global_search(self, *, query_params, user=None):
        if not isinstance(user, AdminUser):
            raise PermissionDenied("Admin search requires platform admin access.")
        params = self.filters.parse(SearchResource.ADMIN, query_params)
        return GlobalSearchSelector().search(
            query=params.get("query", ""),
            domain=params.get("domain", ""),
            resource=params.get("resource", ""),
        )

    def _search_invoices(self, *, user, **params):
        if not isinstance(user, AdminUser):
            raise PermissionDenied("Invoice search requires admin access.")
        return InvoiceSelector().search(**params)

    def _search_guarantees(self, *, user, **params):
        if not isinstance(user, AdminUser):
            raise PermissionDenied("Guarantee search requires admin access.")
        return GuaranteeSearchSelector().search(**params)

    def _search_job_seekers(self, *, user, **params):
        if not isinstance(user, (AdminUser, ITUser)):
            raise PermissionDenied("Job seeker search requires authenticated access.")
        if isinstance(user, ITUser):
            from apps.it_recruitment.services.jobseeker_privacy_service import (
                JobSeekerPrivacyService,
            )

            if not JobSeekerPrivacyService().is_recruiter(user):
                raise PermissionDenied(
                    "Recruiter access required for candidate search."
                )
        return JobSeekerSearchSelector().search(viewer=user, **params)

    def _search_recruiters(self, *, user, **params):
        if not isinstance(user, AdminUser):
            raise PermissionDenied("Recruiter search requires admin access.")
        return RecruiterSearchSelector().search(**params)

    def _search_professors(self, *, user, **params):
        if not isinstance(user, (AdminUser, CollegeUser)):
            raise PermissionDenied("Professor search requires admin or college access.")
        return ProfessorSearchSelector().search(**params)

    def _search_admin(self, *, user, **params):
        return self.global_search(
            query_params={"q": params.get("query", ""), **params}, user=user
        )

    @staticmethod
    def _is_public(user) -> bool:
        return not isinstance(user, AdminUser)
