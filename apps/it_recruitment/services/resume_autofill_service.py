"""Apply parsed resume data to job seeker profile fields and related models."""

from __future__ import annotations

import logging

from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.resume_parsing_service import ResumeParsingService
from apps.it_recruitment.services.resume_profile_mapper import ResumeProfileMapper
from apps.it_recruitment.services.resume_profile_synchronizer import (
    ResumeProfileSynchronizer,
)

logger = logging.getLogger(__name__)


class ResumeAutofillService(BaseService):
    """One-click apply of parsed resume data to Job Seeker profile and related models."""

    @BaseService.atomic
    def apply(
        self, profile: JobSeekerProfile, *, actor_id: int, fields: list[str] | None = None
    ) -> dict:
        if not profile.resume_file_id or not profile.resume_file:
            raise ValidationException("Upload a resume before applying parsed data.")

        parsed = ResumeParsingService().get_extracted(profile.resume_file)
        if not parsed:
            raise ValidationException(
                "Resume parsing is still in progress or not available. Try again shortly."
            )

        # Map parsed JSON to validated profile DTO
        mapped = ResumeProfileMapper().map_parsed_data(parsed)

        # Synchronize mapped data into models atomically
        updated_sections = ResumeProfileSynchronizer().sync(
            profile, mapped, actor_id=actor_id
        )

        return {
            "success": True,
            "message": "Profile updated successfully from resume."
            if updated_sections
            else "Your profile already contains the extracted resume information.",
            "updated_sections": updated_sections,
        }
