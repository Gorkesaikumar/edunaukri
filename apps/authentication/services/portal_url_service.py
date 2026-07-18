"""UUID-scoped portal URL builders — single source for reverse() with user_uuid."""

from __future__ import annotations

from django.urls import reverse

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.services.identity_service import IdentityService


class PortalURLService:
    """Build role-scoped portal URLs that embed the user's permanent UUID."""

    @staticmethod
    def user_uuid(user) -> str:
        return IdentityService.public_uuid(user)

    @staticmethod
    def super_admin(user, view_name: str, **kwargs) -> str:
        kwargs.setdefault("user_uuid", IdentityService.public_uuid(user))
        return reverse(view_name, kwargs=kwargs)

    @staticmethod
    def jobseeker(user, view_name: str, **kwargs) -> str:
        kwargs.setdefault("user_uuid", IdentityService.public_uuid(user))
        return reverse(view_name, kwargs=kwargs)

    @staticmethod
    def recruiter(user, view_name: str, **kwargs) -> str:
        kwargs.setdefault("user_uuid", IdentityService.public_uuid(user))
        return reverse(view_name, kwargs=kwargs)

    @staticmethod
    def professor(user, view_name: str, **kwargs) -> str:
        kwargs.setdefault("user_uuid", IdentityService.public_uuid(user))
        return reverse(view_name, kwargs=kwargs)

    @staticmethod
    def college(user, view_name: str, **kwargs) -> str:
        kwargs.setdefault("user_uuid", IdentityService.public_uuid(user))
        return reverse(view_name, kwargs=kwargs)

    @staticmethod
    def dashboard_for_user(user) -> str:
        if isinstance(user, AdminUser):
            return PortalURLService.super_admin(user, "super_admin_dashboard")
        if isinstance(user, ProfessorUser):
            return PortalURLService.professor(user, "professor_dashboard")
        if isinstance(user, CollegeUser):
            return PortalURLService.college(user, "college_dashboard")
        roles = RoleAssignmentService()
        if roles.user_has_it_role(user, ITUserRoleType.RECRUITER):
            return PortalURLService.recruiter(user, "recruiter_dashboard")
        return PortalURLService.jobseeker(user, "jobseeker_dashboard")

    @staticmethod
    def settings_for_user(user) -> str:
        if isinstance(user, AdminUser):
            return PortalURLService.super_admin(user, "super_admin_settings")
        if isinstance(user, ProfessorUser):
            return PortalURLService.professor(user, "professor_settings")
        if isinstance(user, CollegeUser):
            return PortalURLService.college(user, "college_settings")
        roles = RoleAssignmentService()
        if roles.user_has_it_role(user, ITUserRoleType.RECRUITER):
            return PortalURLService.recruiter(user, "recruiter_settings")
        return PortalURLService.jobseeker(user, "jobseeker_settings")

    @staticmethod
    def scoped_path(prefix: str, user_uuid, subpath: str) -> str:
        """Build a raw path without reverse (for legacy redirect targets)."""
        subpath = subpath.strip("/")
        base = f"/{prefix.strip('/')}/{user_uuid}"
        return f"{base}/{subpath}/" if subpath else f"{base}/"
