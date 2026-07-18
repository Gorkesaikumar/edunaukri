from apps.accounts.profiles.repositories.base import ProfileRepository
from apps.core.repositories.crud import CRUDRepository
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile


class JobSeekerProfileRepository(ProfileRepository):
    model = JobSeekerProfile


class RecruiterProfileRepository(ProfileRepository):
    model = RecruiterProfile
