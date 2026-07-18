from apps.accounts.profiles.repositories.base import ReadOnlyProfileRepository
from apps.academic_recruitment.models import ProfessorProfile
from apps.core.selectors.read import ReadSelector


class ProfessorProfileReadRepository(ReadOnlyProfileRepository):
    model = ProfessorProfile


class ProfessorProfileSelector(ReadSelector):
    model = ProfessorProfile

    def for_user(self, user):
        return self.filter_by(user=user).first()

    def get_active(self, profile_id):
        return self.model.profiles.with_active_status().filter(pk=profile_id).first()
