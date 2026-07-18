from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.academic_recruitment.selectors.profile_selector import (
    ProfessorProfileSelector,
)
from apps.colleges.selectors.college_selector import (
    CollegeMemberSelector,
    CollegeSelector,
)
from apps.core.exceptions.domain_exceptions import ResourceNotFoundException
from apps.core.selectors.read import ReadSelector
from apps.it_recruitment.selectors.profile_selector import (
    JobSeekerProfileSelector,
    RecruiterProfileSelector,
)


class ProfileSelector(ReadSelector):
    """Resolve domain profiles for authenticated users and public lookups."""

    def resolve_profile_type(self, user) -> ProfileType | None:
        if isinstance(user, AdminUser):
            return ProfileType.ADMIN
        if isinstance(user, ITUser):
            roles = RoleAssignmentService().get_it_roles(user)
            if ITUserRoleType.JOB_SEEKER in roles:
                return ProfileType.JOB_SEEKER
            if ITUserRoleType.RECRUITER in roles:
                return ProfileType.RECRUITER
            return None
        if isinstance(user, ProfessorUser):
            return ProfileType.PROFESSOR
        if isinstance(user, CollegeUser):
            return ProfileType.COLLEGE
        return None

    def for_user(self, user, profile_type: ProfileType | None = None):
        profile_type = profile_type or self.resolve_profile_type(user)
        if profile_type == ProfileType.JOB_SEEKER:
            return JobSeekerProfileSelector().for_user(user)
        if profile_type == ProfileType.RECRUITER:
            return RecruiterProfileSelector().for_user(user)
        if profile_type == ProfileType.PROFESSOR:
            return ProfessorProfileSelector().for_user(user)
        if profile_type == ProfileType.COLLEGE:
            membership = CollegeMemberSelector().primary_for_user(user)
            return membership.college if membership else None
        if profile_type == ProfileType.ADMIN:
            return user
        return None

    def get_public_profile(self, profile_type: ProfileType, profile_id):
        if profile_type == ProfileType.JOB_SEEKER:
            profile = JobSeekerProfileSelector().get_active(profile_id)
        elif profile_type == ProfileType.RECRUITER:
            profile = RecruiterProfileSelector().get_active(profile_id)
        elif profile_type == ProfileType.PROFESSOR:
            profile = ProfessorProfileSelector().get_active(profile_id)
        elif profile_type == ProfileType.COLLEGE:
            profile = CollegeSelector().get_active(profile_id)
        else:
            raise ResourceNotFoundException("Public profile not available.")
        if not profile:
            raise ResourceNotFoundException("Profile not found.")
        return profile
