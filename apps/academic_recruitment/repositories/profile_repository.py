from apps.accounts.profiles.repositories.base import ProfileRepository
from apps.academic_recruitment.models import ProfessorProfile


class ProfessorProfileRepository(ProfileRepository):
    model = ProfessorProfile
