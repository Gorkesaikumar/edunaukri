from django.db.models import Avg

from apps.accounts.profiles.constants.enums import ProfileType
from apps.academic_recruitment.models import ProfessorProfile
from apps.colleges.models import College
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile


class ProfileStatisticsSelector(BaseService):
    """Aggregate profile counts for admin dashboards."""

    def overview(self) -> dict:
        return {
            "job_seeker": {
                "total": JobSeekerProfile.profiles.count(),
                "active": JobSeekerProfile.profiles.with_active_status().count(),
            },
            "recruiter": {
                "total": RecruiterProfile.profiles.count(),
                "active": RecruiterProfile.profiles.with_active_status().count(),
            },
            "professor": {
                "total": ProfessorProfile.profiles.count(),
                "active": ProfessorProfile.profiles.with_active_status().count(),
            },
            "college": {
                "total": College.profiles.count(),
                "active": College.profiles.with_active_status().count(),
            },
        }

    def average_completion(self) -> dict:
        return {
            ProfileType.JOB_SEEKER: JobSeekerProfile.profiles.aggregate(
                average=Avg("profile_completeness")
            )["average"]
            or 0,
            ProfileType.PROFESSOR: ProfessorProfile.profiles.aggregate(
                average=Avg("profile_completeness")
            )["average"]
            or 0,
        }
