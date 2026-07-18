from rest_framework import permissions

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.selectors.profile_selector import ProfileSelector
from apps.core.permissions.base import IsPlatformAdmin


class IsProfileOwner(permissions.BasePermission):
    """Authenticated user owns the resolved profile."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if isinstance(request.user, AdminUser):
            return True
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        if not profile_type or profile_type == ProfileType.ADMIN:
            return False
        return ProfileSelector().for_user(request.user, profile_type) is not None


class CanManageOwnProfile(permissions.BasePermission):
    required_profile_type = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        if self.required_profile_type and profile_type != self.required_profile_type:
            return False
        return profile_type is not None and profile_type != ProfileType.ADMIN


class IsJobSeekerProfileOwner(CanManageOwnProfile):
    required_profile_type = ProfileType.JOB_SEEKER


class IsRecruiterProfileOwner(CanManageOwnProfile):
    required_profile_type = ProfileType.RECRUITER


class IsProfessorProfileOwner(CanManageOwnProfile):
    required_profile_type = ProfileType.PROFESSOR


class IsCollegeProfileOwner(CanManageOwnProfile):
    required_profile_type = ProfileType.COLLEGE


class CanViewAnyProfile(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            isinstance(request.user, AdminUser)
            and request.user.is_authenticated
            and request.user.is_active
        )
