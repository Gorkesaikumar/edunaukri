from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.academic_recruitment.models import ProfessorProfile


class ProfessorProfileService(ProfileService):
    @staticmethod
    def create_profile(*, user: ProfessorUser, data: dict) -> ProfessorProfile:
        return ProfileService().create_profile(
            user=user, profile_type=ProfileType.PROFESSOR, data=data
        )
