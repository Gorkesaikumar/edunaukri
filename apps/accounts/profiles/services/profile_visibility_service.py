from apps.accounts.models.admin_user import AdminUser
from apps.accounts.profiles.constants.enums import (
    PRIVATE_PROFILE_FIELDS,
    ProfileStatus,
    ProfileType,
    ProfileVisibility,
)
from apps.core.exceptions.domain_exceptions import PermissionDeniedException
from apps.core.services.base import BaseService


class ProfileVisibilityService(BaseService):
    """Control public vs private profile field exposure."""

    ALWAYS_PUBLIC_FIELDS = frozenset(
        {
            "id",
            "first_name",
            "last_name",
            "headline",
            "summary",
            "specialization",
            "research_interests",
            "current_designation",
            "current_institution",
            "current_company",
            "experience_years",
            "teaching_experience_years",
            "publications_count",
            "name",
            "college_type",
            "city",
            "state",
            "website_url",
            "naac_grade",
            "profile_completeness",
            "profile_visibility",
            "created_at",
        }
    )

    def can_view(self, *, viewer, profile, profile_type: ProfileType) -> bool:
        if isinstance(viewer, AdminUser):
            return True
        if profile_type == ProfileType.ADMIN:
            return isinstance(viewer, AdminUser)

        owner = self._profile_owner(profile, profile_type)
        if (
            viewer is not None
            and getattr(viewer, "is_authenticated", False)
            and owner
            and owner.pk == viewer.pk
        ):
            return True

        if (
            getattr(profile, "profile_status", ProfileStatus.ACTIVE)
            != ProfileStatus.ACTIVE
        ):
            return False

        visibility = getattr(profile, "profile_visibility", ProfileVisibility.PRIVATE)
        if visibility == ProfileVisibility.PUBLIC:
            return True
        if (
            visibility == ProfileVisibility.EMPLOYERS_ONLY
            and profile_type == ProfileType.JOB_SEEKER
            and viewer is not None
            and getattr(viewer, "is_authenticated", False)
        ):
            return self._viewer_is_recruiter(viewer)
        return False

    def to_public_dict(self, data: dict, profile_type: ProfileType) -> dict:
        public = {}
        for key, value in data.items():
            if key in self.ALWAYS_PUBLIC_FIELDS:
                public[key] = value
            elif key not in PRIVATE_PROFILE_FIELDS and not key.endswith("_id"):
                public[key] = value
        public["profile_type"] = profile_type
        return public

    def ensure_can_view(self, *, viewer, profile, profile_type: ProfileType) -> None:
        if not self.can_view(viewer=viewer, profile=profile, profile_type=profile_type):
            raise PermissionDeniedException(
                "You do not have permission to view this profile."
            )

    def _profile_owner(self, profile, profile_type: ProfileType):
        if profile_type in (
            ProfileType.JOB_SEEKER,
            ProfileType.RECRUITER,
            ProfileType.PROFESSOR,
        ):
            return getattr(profile, "user", None)
        return None

    def _viewer_is_recruiter(self, viewer) -> bool:
        from apps.accounts.constants.enums import ITUserRoleType
        from apps.accounts.models.it_user import ITUser
        from apps.accounts.services.role_assignment_service import RoleAssignmentService

        if not isinstance(viewer, ITUser):
            return False
        return ITUserRoleType.RECRUITER in RoleAssignmentService().get_it_roles(viewer)
