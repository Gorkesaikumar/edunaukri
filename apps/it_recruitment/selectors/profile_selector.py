from apps.accounts.profiles.repositories.base import ReadOnlyProfileRepository
from apps.core.selectors.read import ReadSelector
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile


class JobSeekerProfileReadRepository(ReadOnlyProfileRepository):
    model = JobSeekerProfile


class RecruiterProfileReadRepository(ReadOnlyProfileRepository):
    model = RecruiterProfile


class JobSeekerProfileSelector(ReadSelector):
    model = JobSeekerProfile

    def for_user(self, user):
        return self.filter_by(user=user).first()

    def get_active(self, profile_id):
        return self.model.profiles.with_active_status().filter(pk=profile_id).first()


class RecruiterProfileSelector(ReadSelector):
    model = RecruiterProfile

    def for_user(self, user):
        return self.filter_by(user=user).first()

    def get_active(self, profile_id):
        return self.model.profiles.with_active_status().filter(pk=profile_id).first()
