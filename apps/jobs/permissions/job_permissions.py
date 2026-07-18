"""Object-level permissions for the Job Management module."""

from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector
from apps.jobs.selectors.job_selector import JobPostingSelector


class CanManageJob(BasePermission):
    """Allow recruiters that are members of the job's company (admins bypass).

    Resolves ``job_id`` from the view kwargs; when absent (list/create routes)
    it defers to the service layer for company-membership checks.
    """

    message = "You do not manage this job posting."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        job_id = view.kwargs.get("job_id")
        if not job_id:
            return True
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return False
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return True  # let the view return 404
        return CompanyMemberSelector().is_member(recruiter, job.company_id)
