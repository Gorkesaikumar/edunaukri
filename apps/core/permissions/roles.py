from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.it_user import ITUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.core.permissions.base import (
    DomainPermissionBase,
    IsCollegeUser,
    IsFacultyDomainUser,
    IsITDomainUser,
    IsPlatformAdmin,
    IsProfessorUser,
)
from rest_framework.permissions import BasePermission


def _user_it_roles(user) -> list[str]:
    if not isinstance(user, ITUser):
        return []
    return RoleAssignmentService().get_it_roles(user)


class IsJobSeeker(BasePermission):
    def has_permission(self, request, view):
        if not IsITDomainUser().has_permission(request, view):
            return False
        return ITUserRoleType.JOB_SEEKER in _user_it_roles(request.user)


class IsRecruiter(BasePermission):
    def has_permission(self, request, view):
        if not IsITDomainUser().has_permission(request, view):
            return False
        return ITUserRoleType.RECRUITER in _user_it_roles(request.user)


class IsProfessor(IsProfessorUser):
    """Academic domain — professor identity."""


class IsCollege(IsCollegeUser):
    """Academic domain — college representative identity."""


class IsAdmin(IsPlatformAdmin):
    """Platform administrator."""


class IsITJobSeeker(DomainPermissionBase):
    domain = "it"
    required_roles = (ITUserRoleType.JOB_SEEKER,)


class IsITRecruiter(DomainPermissionBase):
    domain = "it"
    required_roles = (ITUserRoleType.RECRUITER,)


__all__ = [
    "IsAdmin",
    "IsPlatformAdmin",
    "IsITDomainUser",
    "IsProfessor",
    "IsProfessorUser",
    "IsCollege",
    "IsCollegeUser",
    "IsFacultyDomainUser",
    "IsJobSeeker",
    "IsRecruiter",
    "IsITJobSeeker",
    "IsITRecruiter",
    "DomainPermissionBase",
]
