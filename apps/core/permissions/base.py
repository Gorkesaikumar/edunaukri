from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.faculty_user import FacultyUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser


class IsPlatformAdmin(BasePermission):
    """Allow access only to authenticated AdminUser instances."""

    def has_permission(self, request, view):
        return isinstance(request.user, AdminUser) and request.user.is_active


class IsITDomainUser(BasePermission):
    """Allow access only to authenticated IT domain users."""

    def has_permission(self, request, view):
        return isinstance(request.user, ITUser) and request.user.is_active


class IsProfessorUser(BasePermission):
    """Allow access only to authenticated professor users."""

    def has_permission(self, request, view):
        return isinstance(request.user, ProfessorUser) and request.user.is_active


class IsCollegeUser(BasePermission):
    """Allow access only to authenticated college users."""

    def has_permission(self, request, view):
        return isinstance(request.user, CollegeUser) and request.user.is_active


class IsFacultyDomainUser(BasePermission):
    """Legacy — professor or college user."""

    def has_permission(self, request, view):
        return (
            isinstance(request.user, (ProfessorUser, CollegeUser, FacultyUser))
            and request.user.is_active
        )


from apps.accounts.services.role_assignment_service import RoleAssignmentService


class DomainPermissionBase(BasePermission):
    """Domain + optional IT role permission checks."""

    domain = None
    required_roles = ()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        user_domain = getattr(request.user, "domain", None)
        if self.domain and user_domain != self.domain:
            return False
        if self.required_roles:
            user_roles = RoleAssignmentService().get_it_roles(request.user)
            return any(role in user_roles for role in self.required_roles)
        return True
