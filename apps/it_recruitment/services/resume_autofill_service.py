"""Apply parsed resume data to job seeker profile fields."""

from __future__ import annotations

from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.it_recruitment.services.resume_parsing_service import ResumeParsingService


class ResumeAutofillService(BaseService):
    """One-click apply of parsed resume fields after user confirmation."""

    @BaseService.atomic
    def apply(
        self, profile: JobSeekerProfile, *, actor_id, fields: list[str] | None = None
    ) -> dict:
        if not profile.resume_file_id or not profile.resume_file:
            raise ValidationException("Upload a resume before applying parsed data.")

        parsed = ResumeParsingService().get_extracted(profile.resume_file)
        if not parsed:
            raise ValidationException(
                "Resume parsing is still in progress. Try again shortly."
            )

        allowed = fields or ["phone", "skills"]
        applied: list[str] = []
        profile_updates: dict = {}

        if (
            "phone" in allowed
            and parsed.get("phone")
            and not (profile.phone or "").strip()
        ):
            profile_updates["phone"] = parsed["phone"][:20]
            applied.append("phone")

        if profile_updates:
            ProfileService().update_profile(
                user=profile.user,
                profile_type=ProfileType.JOB_SEEKER,
                data=profile_updates,
            )
            profile.refresh_from_db()

        if "skills" in allowed and parsed.get("skills"):
            existing = {
                s.lower()
                for s in profile.skills.filter(is_deleted=False).values_list(
                    "skill__name", flat=True
                )
            }
            new_skills = [s for s in parsed["skills"] if s.lower() not in existing]
            if new_skills:
                merged = (
                    list(
                        profile.skills.filter(is_deleted=False).values_list(
                            "skill__name", flat=True
                        )
                    )
                    + new_skills[:20]
                )
                ProfileService().update_profile(
                    user=profile.user,
                    profile_type=ProfileType.JOB_SEEKER,
                    data={"skills": merged[:50]},
                )
                applied.append("skills")

        if not applied:
            raise ValidationException(
                "No empty profile fields matched the parsed resume data."
            )

        JobSeekerProfileCompletionService().recalculate(profile)
        from apps.it_recruitment.services.job_recommendation_trigger_service import (
            JobRecommendationTriggerService,
        )

        JobRecommendationTriggerService.after_profile_mutation(
            profile.pk, reason="resume_autofill"
        )

        return {
            "applied_fields": applied,
            "parsed_preview": {k: parsed.get(k) for k in applied if k in parsed},
        }
