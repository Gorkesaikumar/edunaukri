"""Object-level permissions for the College / Institution Management module."""

from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.colleges.selectors.college_selector import CollegeMemberSelector


def _college_id_from_view(view):
    return view.kwargs.get("college_id")


class IsInstitutionMember(BasePermission):
    """Allow access when the college user belongs to the target institution."""

    message = "You are not a member of this institution."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        college_id = _college_id_from_view(view)
        if not college_id:
            return True
        return CollegeMemberSelector().is_member(request.user, college_id)


class IsInstitutionAdmin(BasePermission):
    """Allow access only to institution administrators (owner/admin)."""

    message = "Only institution administrators can perform this action."

    def has_permission(self, request, view):
        if isinstance(request.user, AdminUser):
            return True
        college_id = _college_id_from_view(view)
        if not college_id:
            return True
        return CollegeMemberSelector().is_admin(request.user, college_id)
