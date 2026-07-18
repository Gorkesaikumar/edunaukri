"""Dynamic profile completion for IT job seeker dashboards."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.utils import timezone

from apps.authentication.services.portal_url_service import PortalURLService

from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_completion_service import (
    ProfileCompletionService,
    _filled,
)
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile


@dataclass
class ProfileSectionStatus:
    key: str
    label: str
    completed: bool
    weight: int


@dataclass
class ProfileCompletionResult:
    percentage: int
    status_label: str
    sections: list[ProfileSectionStatus]

    def to_dict(self) -> dict:
        return {
            "percentage": self.percentage,
            "status_label": self.status_label,
            "sections": [
                {
                    "key": s.key,
                    "label": s.label,
                    "completed": s.completed,
                    "weight": s.weight,
                }
                for s in self.sections
            ],
        }


@dataclass
class ProfileCompletionDashboardState:
    """Backend-driven UI state for the profile completion hero card."""

    percentage: int
    status_label: str
    show_completion_card: bool
    play_celebration: bool
    celebration_message: str
    profile_completed: bool
    completion_animation_shown: bool
    profile_completed_at: str | None
    sections: list[ProfileSectionStatus]
    mark_animation_url: str = ""

    def to_dict(self) -> dict:
        return {
            "percentage": self.percentage,
            "status_label": self.status_label,
            "show_completion_card": self.show_completion_card,
            "play_celebration": self.play_celebration,
            "celebration_message": self.celebration_message,
            "profile_completed": self.profile_completed,
            "completion_animation_shown": self.completion_animation_shown,
            "profile_completed_at": self.profile_completed_at,
            "sections": [
                {
                    "key": s.key,
                    "label": s.label,
                    "completed": s.completed,
                    "weight": s.weight,
                }
                for s in self.sections
            ],
            "mark_animation_url": self.mark_animation_url,
        }


class JobSeekerProfileCompletionService(BaseService):
    """Calculate, persist, and expose job seeker profile completion state."""

    STATUS_THRESHOLDS = (
        (100, "Complete"),
        (90, "Excellent"),
        (70, "Almost There"),
        (40, "Good Progress"),
        (0, "Getting Started"),
    )

    CELEBRATION_MESSAGES = (
        "🎉 Congratulations! Your profile is now 100% complete.",
        "Excellent! Your profile is ready for recruiters.",
        "Your profile is now fully optimized for better job matching.",
    )

    PERSIST_FIELDS = (
        "profile_completeness",
        "profile_completed",
        "completion_animation_shown",
        "profile_completed_at",
        "profile_completion_fingerprint",
        "updated_at",
    )

    def get_dashboard_state(
        self, profile: JobSeekerProfile
    ) -> ProfileCompletionDashboardState:
        """Return stored completion state for fast dashboard rendering."""
        if not profile.profile_completion_fingerprint:
            return self.recalculate(profile)

        percentage = profile.profile_completeness
        return self._build_dashboard_state(
            profile,
            ProfileCompletionResult(
                percentage=percentage,
                status_label=self._status_label(percentage),
                sections=[],
            ),
        )

    def recalculate(self, profile: JobSeekerProfile) -> ProfileCompletionDashboardState:
        """Recalculate completion from live profile data and persist all flags."""
        was_untracked = not profile.profile_completion_fingerprint
        result = self.evaluate(profile, persist=False)
        fingerprint = self._compute_fingerprint(profile, result.sections)
        self._sync_completion_flags(profile, result.percentage)

        profile.profile_completeness = result.percentage
        profile.profile_completion_fingerprint = fingerprint

        # Legacy profiles already at 100% should not replay the celebration.
        if was_untracked and result.percentage == 100:
            profile.completion_animation_shown = True

        profile.save(update_fields=list(self.PERSIST_FIELDS))

        return self._build_dashboard_state(profile, result)

    def mark_celebration_shown(
        self, profile: JobSeekerProfile
    ) -> ProfileCompletionDashboardState:
        """Persist that the one-time celebration animation has been displayed."""
        if not profile.completion_animation_shown:
            profile.completion_animation_shown = True
            profile.save(update_fields=["completion_animation_shown", "updated_at"])
        return self.get_dashboard_state(profile)

    def evaluate(
        self, profile: JobSeekerProfile, *, persist: bool = False
    ) -> ProfileCompletionResult:
        sections = self._build_sections(profile)
        total_weight = sum(s.weight for s in sections)
        earned = sum(s.weight for s in sections if s.completed)
        percentage = round((earned / total_weight) * 100) if total_weight else 0
        percentage = min(100, max(0, percentage))
        status_label = self._status_label(percentage)

        if persist:
            self.recalculate(profile)
            return ProfileCompletionResult(
                percentage=profile.profile_completeness,
                status_label=self._status_label(profile.profile_completeness),
                sections=sections,
            )

        return ProfileCompletionResult(
            percentage=percentage, status_label=status_label, sections=sections
        )

    def _build_dashboard_state(
        self,
        profile: JobSeekerProfile,
        result: ProfileCompletionResult,
    ) -> ProfileCompletionDashboardState:
        show_card = result.percentage < 100 or (
            result.percentage == 100 and not profile.completion_animation_shown
        )
        play_celebration = (
            result.percentage == 100
            and profile.profile_completed
            and not profile.completion_animation_shown
        )
        celebration_message = self.CELEBRATION_MESSAGES[0] if play_celebration else ""

        return ProfileCompletionDashboardState(
            percentage=result.percentage,
            status_label=result.status_label,
            show_completion_card=show_card,
            play_celebration=play_celebration,
            celebration_message=celebration_message,
            profile_completed=profile.profile_completed,
            completion_animation_shown=profile.completion_animation_shown,
            profile_completed_at=(
                profile.profile_completed_at.isoformat()
                if profile.profile_completed_at
                else None
            ),
            sections=result.sections,
            mark_animation_url=PortalURLService.jobseeker(
                profile.user, "jobseeker_profile_completion_animation_api"
            ),
        )

    def _sync_completion_flags(
        self, profile: JobSeekerProfile, percentage: int
    ) -> None:
        now = timezone.now()
        if percentage < 100:
            profile.profile_completed = False
            profile.completion_animation_shown = False
            profile.profile_completed_at = None
            return

        if not profile.profile_completed:
            profile.profile_completed = True
            profile.profile_completed_at = now

    def _compute_fingerprint(
        self, profile: JobSeekerProfile, sections: list[ProfileSectionStatus]
    ) -> str:
        resume_fp = ""
        if profile.resume_file_id and profile.resume_file:
            cache = (profile.resume_file.parsed_data or {}).get("dashboard_cache", {})
            resume_fp = str(cache.get("fingerprint", ""))
        section_sig = "|".join(f"{s.key}:{int(s.completed)}" for s in sections)
        payload = f"{profile.pk}:{resume_fp}:{section_sig}"
        return hashlib.sha256(payload.encode()).hexdigest()[:64]

    def _build_sections(self, profile: JobSeekerProfile) -> list[ProfileSectionStatus]:
        resume_data = {}
        if (
            profile.resume_file_id
            and profile.resume_file
            and profile.resume_file.parsed_data
        ):
            resume_data = profile.resume_file.parsed_data.get("dashboard_cache", {})

        has_personal = all(
            [
                _filled(profile.first_name),
                _filled(profile.last_name),
                _filled(profile.phone),
            ]
        )
        has_skills = profile.skills.filter(is_deleted=False).exists()
        has_experience = profile.experiences.filter(is_deleted=False).exists()
        has_education = profile.education.filter(is_deleted=False).exists()
        has_social = any(
            [
                _filled(profile.linkedin_url),
                _filled(profile.github_url),
                _filled(profile.portfolio_url),
            ]
        )
        has_projects = profile.projects.filter(is_deleted=False).exists() or bool(
            resume_data.get("projects")
        )
        has_certifications = profile.certifications.filter(
            is_deleted=False
        ).exists() or bool(resume_data.get("certifications"))
        has_preferred_role = _filled(profile.headline) or bool(
            isinstance(profile.preferred_roles, list) and profile.preferred_roles
        )
        has_career_prefs = (
            _filled(profile.employment_type_preference)
            or profile.notice_period_days is not None
        )

        checks = [
            ProfileSectionStatus("personal", "Personal Information", has_personal, 8),
            ProfileSectionStatus(
                "photo", "Profile Photo", profile.profile_photo_id is not None, 6
            ),
            ProfileSectionStatus(
                "resume", "Resume Uploaded", profile.resume_file_id is not None, 10
            ),
            ProfileSectionStatus("skills", "Skills Added", has_skills, 10),
            ProfileSectionStatus("education", "Education Added", has_education, 8),
            ProfileSectionStatus("experience", "Experience Added", has_experience, 10),
            ProfileSectionStatus("projects", "Projects Added", has_projects, 6),
            ProfileSectionStatus(
                "certifications", "Certifications Added", has_certifications, 6
            ),
            ProfileSectionStatus(
                "preferred_roles", "Preferred Job Roles", has_preferred_role, 6
            ),
            ProfileSectionStatus(
                "preferred_locations",
                "Preferred Locations",
                _filled(profile.preferred_location)
                or _filled(profile.current_location),
                6,
            ),
            ProfileSectionStatus(
                "expected_salary",
                "Expected Salary",
                profile.expected_salary is not None,
                5,
            ),
            ProfileSectionStatus(
                "portfolio", "Portfolio / GitHub / LinkedIn", has_social, 6
            ),
            ProfileSectionStatus(
                "summary", "Professional Summary", _filled(profile.summary), 8
            ),
            ProfileSectionStatus(
                "career_preferences", "Career Preferences", has_career_prefs, 5
            ),
        ]
        return checks

    @staticmethod
    def _status_label(percentage: int) -> str:
        for threshold, label in JobSeekerProfileCompletionService.STATUS_THRESHOLDS:
            if percentage >= threshold:
                return label
        return "Getting Started"

    @staticmethod
    def legacy_calculate(profile: JobSeekerProfile) -> int:
        """Fallback via shared accounts completion service."""
        return ProfileCompletionService().calculate(profile, ProfileType.JOB_SEEKER)
