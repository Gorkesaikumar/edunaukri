"""Profile completion state and celebration workflow for professor dashboard."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.utils import timezone

from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_completion_service import (
    ProfileCompletionService,
    _filled,
)
from apps.academic_recruitment.models import ProfessorProfile
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService


@dataclass
class CompletionChecklistItem:
    key: str
    label: str
    completed: bool
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "completed": self.completed,
            "url": self.url,
        }


@dataclass
class ProfessorProfileCompletionState:
    percentage: int
    status_label: str
    checklist: list[CompletionChecklistItem]
    show_completion_card: bool = False
    play_celebration: bool = False
    celebration_message: str = ""
    profile_completed: bool = False
    completion_animation_shown: bool = False
    profile_completed_at: str | None = None
    mark_animation_url: str = ""
    remaining_count: int = 0
    completed_count: int = 0
    total_count: int = 10
    strength_label: str = "Getting Started"

    def to_dict(self) -> dict:
        return {
            "percentage": self.percentage,
            "status_label": self.status_label,
            "checklist": [item.to_dict() for item in self.checklist],
            "show_completion_card": self.show_completion_card,
            "play_celebration": self.play_celebration,
            "celebration_message": self.celebration_message,
            "profile_completed": self.profile_completed,
            "completion_animation_shown": self.completion_animation_shown,
            "profile_completed_at": self.profile_completed_at,
            "mark_animation_url": self.mark_animation_url,
            "remaining_count": self.remaining_count,
            "completed_count": self.completed_count,
            "total_count": self.total_count,
            "strength_label": self.strength_label,
        }


class ProfessorProfileCompletionService(BaseService):
    STATUS_THRESHOLDS = (
        (100, "Complete"),
        (90, "Excellent"),
        (70, "Almost There"),
        (40, "Good Progress"),
        (0, "Getting Started"),
    )

    CELEBRATION_MESSAGES = (
        "Congratulations! Your faculty profile is now 100% complete.",
        "Excellent! Your profile is ready for institutions.",
        "Your profile is fully optimized for better vacancy matching.",
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
        self, profile: ProfessorProfile | None
    ) -> ProfessorProfileCompletionState:
        if profile is None:
            return ProfessorProfileCompletionState(
                percentage=0,
                status_label="Getting Started",
                checklist=[],
                remaining_count=10,
                completed_count=0,
                total_count=10,
                strength_label="Getting Started",
            )
        if not profile.profile_completion_fingerprint:
            return self.recalculate(profile)
        percentage = profile.profile_completeness
        checklist = self._build_checklist(profile)
        return self._build_dashboard_state(profile, percentage, checklist)

    def recalculate(self, profile: ProfessorProfile) -> ProfessorProfileCompletionState:
        was_untracked = not profile.profile_completion_fingerprint
        percentage = ProfileCompletionService().calculate(
            profile, ProfileType.PROFESSOR
        )
        checklist = self._build_checklist(profile)
        fingerprint = self._compute_fingerprint(profile, checklist)
        self._sync_completion_flags(profile, percentage)

        profile.profile_completeness = percentage
        profile.profile_completion_fingerprint = fingerprint
        if was_untracked and percentage == 100:
            profile.completion_animation_shown = True
        profile.save(update_fields=list(self.PERSIST_FIELDS))
        return self._build_dashboard_state(profile, percentage, checklist)

    def mark_celebration_shown(
        self, profile: ProfessorProfile
    ) -> ProfessorProfileCompletionState:
        if not profile.completion_animation_shown:
            profile.completion_animation_shown = True
            profile.save(update_fields=["completion_animation_shown", "updated_at"])
        percentage = profile.profile_completeness
        if not profile.profile_completion_fingerprint:
            percentage = ProfileCompletionService().calculate(
                profile, ProfileType.PROFESSOR
            )
        checklist = self._build_checklist(profile)
        return self._build_dashboard_state(profile, percentage, checklist)

    def _build_dashboard_state(
        self,
        profile: ProfessorProfile,
        percentage: int,
        checklist: list[CompletionChecklistItem],
    ) -> ProfessorProfileCompletionState:
        show_card = percentage < 100 or (
            percentage == 100 and not profile.completion_animation_shown
        )
        play_celebration = (
            percentage == 100
            and profile.profile_completed
            and not profile.completion_animation_shown
        )
        completed_count = sum(1 for item in checklist if item.completed)
        total_count = len(checklist)
        remaining_count = total_count - completed_count
        status_lbl = self._status_label(percentage)
        return ProfessorProfileCompletionState(
            percentage=percentage,
            status_label=status_lbl,
            checklist=checklist,
            show_completion_card=show_card,
            play_celebration=play_celebration,
            celebration_message=self.CELEBRATION_MESSAGES[0]
            if play_celebration
            else "",
            profile_completed=profile.profile_completed,
            completion_animation_shown=profile.completion_animation_shown,
            profile_completed_at=(
                profile.profile_completed_at.isoformat()
                if profile.profile_completed_at
                else None
            ),
            mark_animation_url=PortalURLService.professor(
                profile.user, "professor_profile_completion_animation_api"
            ),
            remaining_count=remaining_count,
            completed_count=completed_count,
            total_count=total_count,
            strength_label=status_lbl,
        )

    def _sync_completion_flags(
        self, profile: ProfessorProfile, percentage: int
    ) -> None:
        if percentage < 100:
            profile.profile_completed = False
            profile.completion_animation_shown = False
            profile.profile_completed_at = None
            return
        if not profile.profile_completed:
            profile.profile_completed = True
            profile.profile_completed_at = timezone.now()

    def _compute_fingerprint(
        self, profile: ProfessorProfile, checklist: list[CompletionChecklistItem]
    ) -> str:
        section_sig = "|".join(
            f"{item.key}:{int(item.completed)}" for item in checklist
        )
        payload = f"{profile.pk}:{profile.cv_file_id or ''}:{section_sig}"
        return hashlib.sha256(payload.encode()).hexdigest()[:64]

    def _build_checklist(
        self, profile: ProfessorProfile
    ) -> list[CompletionChecklistItem]:
        profile_url = PortalURLService.professor(profile.user, "professor_profile")
        cert_url = PortalURLService.professor(profile.user, "professor_certificates")
        resume_url = PortalURLService.professor(profile.user, "professor_resume")
        has_qualifications = profile.qualifications.filter(is_deleted=False).exists()
        has_certificates = (
            profile.certifications.filter(is_deleted=False).exists()
            or profile.qualifications.filter(
                is_deleted=False, certificate_file__isnull=False
            ).exists()
        )
        has_experience = (
            profile.teaching_experience_years is not None
            or profile.industry_experience_years is not None
            or profile.experience_years is not None
        )
        has_social = (
            _filled(getattr(profile, "linkedin_url", None))
            or _filled(getattr(profile, "google_scholar_url", None))
            or _filled(getattr(profile, "website_url", None))
            or (profile.publications_count > 0)
        )
        has_languages = _filled(getattr(profile, "languages", None)) or bool(
            profile.preferred_locations
        )
        return [
            CompletionChecklistItem(
                key="personal",
                label="Personal Information",
                completed=_filled(profile.first_name)
                and _filled(profile.last_name)
                and _filled(profile.phone),
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="education",
                label="Education",
                completed=has_qualifications or _filled(profile.highest_qualification),
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="experience",
                label="Experience",
                completed=has_experience or _filled(profile.current_designation),
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="skills",
                label="Skills & Specialization",
                completed=_filled(profile.specialization)
                and _filled(profile.research_interests),
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="resume",
                label="Resume / CV",
                completed=profile.cv_file_id is not None,
                url=resume_url,
            ),
            CompletionChecklistItem(
                key="certifications",
                label="Certifications",
                completed=has_certificates,
                url=cert_url,
            ),
            CompletionChecklistItem(
                key="photo",
                label="Profile Photo",
                completed=profile.profile_photo_id is not None,
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="locations",
                label="Preferred Locations",
                completed=bool(profile.preferred_locations),
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="languages",
                label="Languages",
                completed=has_languages,
                url=profile_url,
            ),
            CompletionChecklistItem(
                key="social",
                label="Social Links",
                completed=has_social,
                url=profile_url,
            ),
        ]

    @staticmethod
    def _status_label(percentage: int) -> str:
        for threshold, label in ProfessorProfileCompletionService.STATUS_THRESHOLDS:
            if percentage >= threshold:
                return label
        return "Getting Started"
