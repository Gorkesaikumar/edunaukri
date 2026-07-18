"""Professor research & publications portal page."""

from __future__ import annotations

from dataclasses import dataclass

from apps.academic_recruitment.models import ProfessorProfile
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService


@dataclass
class ResearchQualificationRow:
    name: str
    institution_name: str
    year_obtained: int | None
    has_certificate: bool


@dataclass
class ProfessorResearchPageContext:
    publications_count: int
    research_interests: str
    specialization: str
    qualifications: list[ResearchQualificationRow]
    profile_edit_url: str
    has_research: bool


class ProfessorResearchPortalService(BaseService):
    def build(self, profile: ProfessorProfile) -> ProfessorResearchPageContext:
        qualifications = [
            ResearchQualificationRow(
                name=row.qualification.name,
                institution_name=row.institution_name or "—",
                year_obtained=row.year_obtained,
                has_certificate=row.certificate_file_id is not None,
            )
            for row in profile.qualifications.filter(is_deleted=False).select_related(
                "qualification"
            )
        ]
        research = (profile.research_interests or "").strip()
        return ProfessorResearchPageContext(
            publications_count=profile.publications_count or 0,
            research_interests=research,
            specialization=profile.specialization or "",
            qualifications=qualifications,
            profile_edit_url=PortalURLService.professor(
                profile.user, "professor_profile"
            )
            + "#research",
            has_research=bool(
                research or qualifications or (profile.publications_count or 0)
            ),
        )
