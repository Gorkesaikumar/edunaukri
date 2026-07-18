"""Determines if a faculty profile is eligible to apply for a vacancy."""

from dataclasses import dataclass
from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.applications.models import FacultyApplication
from apps.faculty.models import FacultyVacancy
from apps.core.services.base import BaseService

@dataclass
class ApplicationEligibilityResult:
    eligible: bool
    profile_completion: int
    resume_uploaded: bool
    missing_sections: list[str]
    message: str

    def to_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "profile_completion": self.profile_completion,
            "resume_uploaded": self.resume_uploaded,
            "missing_sections": self.missing_sections,
            "message": self.message,
        }

class FacultyApplicationEligibilityService(BaseService):
    def check(
        self, profile: ProfessorProfile, vacancy: FacultyVacancy
    ) -> ApplicationEligibilityResult:
        if not vacancy.accepts_applications:
            return ApplicationEligibilityResult(
                eligible=False,
                profile_completion=profile.profile_completeness,
                resume_uploaded=bool(profile.cv_file_id),
                missing_sections=[],
                message="This vacancy is no longer accepting applications.",
            )

        has_applied = FacultyApplication.objects.filter(
            professor=profile, vacancy=vacancy, is_deleted=False
        ).exists()
        if has_applied:
            return ApplicationEligibilityResult(
                eligible=False,
                profile_completion=profile.profile_completeness,
                resume_uploaded=bool(profile.cv_file_id),
                missing_sections=[],
                message="You have already applied for this vacancy.",
            )

        completion_svc = ProfessorProfileCompletionService()
        completion = completion_svc.get_dashboard_state(profile)
        
        # We enforce that the resume, personal info, education, and experience must be complete
        # to apply, even if it's not strictly 100% (e.g. they skipped social links).
        missing_mandatory = []
        mandatory_keys = {"personal", "education", "experience", "resume"}
        
        for item in completion.checklist:
            if not item.completed and item.key in mandatory_keys:
                missing_mandatory.append(item.label)

        if missing_mandatory:
            return ApplicationEligibilityResult(
                eligible=False,
                profile_completion=completion.percentage,
                resume_uploaded=bool(profile.cv_file_id),
                missing_sections=missing_mandatory,
                message="Complete your profile before applying.",
            )

        return ApplicationEligibilityResult(
            eligible=True,
            profile_completion=completion.percentage,
            resume_uploaded=bool(profile.cv_file_id),
            missing_sections=[],
            message="You are eligible to apply.",
        )
