from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.selectors.profile_selector import ProfileSelector
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.services.base import BaseService


class UserContextSelector(BaseService):
    """Read-side user context for profile initialization checks."""

    def __init__(self):
        self.profile_selector = ProfileSelector()

    def build_context(self, user) -> dict:
        if isinstance(user, AdminUser):
            return self._admin_context(user)
        if isinstance(user, ITUser):
            return self._it_context(user)
        if isinstance(user, ProfessorUser):
            return self._professor_context(user)
        if isinstance(user, CollegeUser):
            return self._college_context(user)
        return {"domain": getattr(user, "domain", "unknown")}

    def _base(self, user) -> dict:
        return {
            "id": str(user.pk),
            "email": user.email,
            "domain": user.domain,
            "account_status": user.account_status,
            "is_active": user.is_active,
            "email_verified": getattr(user, "email_verified", True),
            "is_locked": user.is_locked,
        }

    def _attach_profile_metadata(self, ctx: dict, user) -> dict:
        profile_type = self.profile_selector.resolve_profile_type(user)
        if profile_type in (None, ProfileType.ADMIN):
            return ctx
        profile = self.profile_selector.for_user(user, profile_type)
        ctx["profile_initialized"] = profile is not None
        if profile:
            ctx["profile_status"] = getattr(profile, "profile_status", None)
            completeness = getattr(profile, "profile_completeness", None)
            if completeness is not None:
                ctx["profile_completeness"] = completeness
        return ctx

    def _admin_context(self, user) -> dict:
        ctx = self._base(user)
        ctx["role"] = "admin"
        ctx["profile_initialized"] = True
        return ctx

    def _it_context(self, user) -> dict:
        roles = RoleAssignmentService().get_it_roles(user)
        ctx = self._base(user)
        ctx["roles"] = roles
        ctx["primary_role"] = roles[0] if roles else None
        return self._attach_profile_metadata(ctx, user)

    def _professor_context(self, user) -> dict:
        ctx = self._base(user)
        ctx["role"] = "professor"
        return self._attach_profile_metadata(ctx, user)

    def _college_context(self, user) -> dict:
        ctx = self._base(user)
        ctx["role"] = "college"
        membership = CollegeMemberSelector().primary_for_user(user)
        ctx["profile_initialized"] = membership is not None
        if membership:
            ctx["college_id"] = str(membership.college_id)
            college = membership.college
            ctx["profile_status"] = getattr(college, "profile_status", None)
        return ctx
