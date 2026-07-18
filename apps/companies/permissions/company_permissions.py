"""Object-level permissions for the Company Management module.

These complement the role-level `IsRecruiter` / `IsPlatformAdmin` checks by
verifying that the authenticated recruiter is a member (or owner) of the
company referenced in the URL.
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector


def _company_id_from_view(view):
    return view.kwargs.get("company_id")


class IsCompanyMember(BasePermission):
    """Allow access when the recruiter belongs to the target company (admins bypass)."""

    message = "You are not a member of this company."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        company_id = _company_id_from_view(view)
        if not company_id:
            return True
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return False
        return CompanyMemberSelector().is_member(recruiter, company_id)


class IsCompanyOwner(BasePermission):
    """Allow access only to the company owner (admins bypass)."""

    message = "Only the company owner can perform this action."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        company_id = _company_id_from_view(view)
        if not company_id:
            return True
        recruiter = RecruiterProfileSelector().for_user(request.user)
        if not recruiter:
            return False
        return CompanyMemberSelector().is_owner(recruiter, company_id)
