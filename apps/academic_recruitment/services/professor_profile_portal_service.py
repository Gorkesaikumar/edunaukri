"""Professor profile read-only portal page."""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_portal_helpers import media_url
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService


@dataclass
class ProfileSection:
    key: str
    label: str
    value: str
    completed: bool


@dataclass
class ProfessorProfilePageContext:
    full_name: str
    headline: str
    avatar_url: str | None
    email: str
    phone: str
    specialization: str
    current_institution: str
    current_designation: str
    publications_count: int
    completion: dict
    sections: list[ProfileSection]
    edit_url: str
    has_cv: bool


class ProfessorProfilePortalService(BaseService):
    def build(self, profile: ProfessorProfile) -> ProfessorProfilePageContext:
        completion = (
            ProfessorProfileCompletionService().get_dashboard_state(profile).to_dict()
        )
        sections = [
            ProfileSection(
                "personal",
                "Personal Information",
                profile.full_name,
                bool(profile.first_name and profile.last_name),
            ),
            ProfileSection(
                "education",
                "Education",
                profile.highest_qualification or "Not added",
                bool(
                    profile.highest_qualification
                    or profile.qualifications.filter(is_deleted=False).exists()
                ),
            ),
            ProfileSection(
                "experience",
                "Experience",
                profile.current_designation or "Not added",
                bool(profile.current_designation or profile.experience_years),
            ),
            ProfileSection(
                "research",
                "Research Interests",
                (profile.research_interests or "Not added")[:120],
                bool(profile.research_interests),
            ),
            ProfileSection(
                "resume",
                "Resume / CV",
                "Uploaded" if profile.cv_file_id else "Not uploaded",
                profile.cv_file_id is not None,
            ),
        ]

        headline_parts = [
            p for p in [profile.current_designation, profile.specialization] if p
        ]

        return ProfessorProfilePageContext(
            full_name=profile.full_name,
            headline=" • ".join(headline_parts)
            if headline_parts
            else "Faculty Job Seeker",
            avatar_url=media_url(profile.profile_photo),
            email=profile.user.email,
            phone=profile.phone or "",
            specialization=profile.specialization or "",
            current_institution=profile.current_institution or "",
            current_designation=profile.current_designation or "",
            publications_count=profile.publications_count or 0,
            completion=completion,
            sections=sections,
            edit_url=PortalURLService.professor(profile.user, "professor_profile"),
            has_cv=profile.cv_file_id is not None,
        )
