"""Synchronize mapped AI resume data into Job Seeker profile models with smart merging and atomic safety."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

from apps.core.services.base import BaseService
from apps.it_recruitment.models import (
    JobSeekerCertification,
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProfile,
    JobSeekerProject,
)
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.it_recruitment.services.resume_profile_mapper import MappedProfileData
from apps.jobs.models import JobSeekerSkill, Skill

logger = logging.getLogger(__name__)


class ResumeProfileSynchronizer(BaseService):
    """Orchestrate atomic updates & smart merging of extracted resume data to profile models."""

    @BaseService.atomic
    def sync(
        self, profile: JobSeekerProfile, mapped: MappedProfileData, *, actor_id: int
    ) -> list[str]:
        updated_sections: set[str] = set()

        logger.info(
            "Starting resume profile synchronization for user_id=%s, profile_id=%s",
            profile.user_id,
            profile.pk,
        )

        # 1. Update Profile Primitive & List Fields
        if mapped.profile_fields:
            section_updated = self._sync_profile_fields(profile, mapped.profile_fields, actor_id=actor_id)
            if section_updated:
                updated_sections.add("Personal Information")

        # 2. Sync Skills
        if mapped.skills:
            if self._sync_skills(profile, mapped.skills, actor_id=actor_id):
                updated_sections.add("Skills")

        # 3. Sync Experiences
        if mapped.experiences:
            if self._sync_experiences(profile, mapped.experiences, actor_id=actor_id):
                updated_sections.add("Experience")

        # 4. Sync Education
        if mapped.education:
            if self._sync_education(profile, mapped.education, actor_id=actor_id):
                updated_sections.add("Education")

        # 5. Sync Projects
        if mapped.projects:
            if self._sync_projects(profile, mapped.projects, actor_id=actor_id):
                updated_sections.add("Projects")

        # 6. Sync Certifications
        if mapped.certifications:
            if self._sync_certifications(profile, mapped.certifications, actor_id=actor_id):
                updated_sections.add("Certifications")

        # 7. Recalculate Completeness and Trigger Downstream Insights
        if updated_sections:
            JobSeekerProfileCompletionService().recalculate(profile)
            try:
                from apps.it_recruitment.services.job_recommendation_trigger_service import (
                    JobRecommendationTriggerService,
                )

                JobRecommendationTriggerService.after_profile_mutation(
                    profile.pk, reason="resume_profile_sync"
                )
            except Exception as exc:
                logger.warning(
                    "Recommendation trigger failed after resume sync for profile_id=%s: %s",
                    profile.pk,
                    exc,
                )

        sections_list = sorted(list(updated_sections))
        logger.info(
            "Completed resume profile synchronization for profile_id=%s. Updated sections: %s",
            profile.pk,
            sections_list,
        )
        return sections_list

    def _sync_profile_fields(
        self, profile: JobSeekerProfile, fields: dict[str, Any], *, actor_id: int
    ) -> bool:
        changed_fields: list[str] = []

        # Scalar / string fields: populate if empty
        scalar_keys = [
            "phone",
            "headline",
            "summary",
            "city",
            "state",
            "country",
            "current_location",
            "preferred_location",
            "current_company",
            "experience_years",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "personal_website",
        ]

        for key in scalar_keys:
            if key not in fields:
                continue
            new_val = fields[key]
            curr_val = getattr(profile, key, None)

            # Preserving existing data rule: fill only if current is empty/None
            if curr_val is None or (isinstance(curr_val, str) and not curr_val.strip()):
                setattr(profile, key, new_val)
                changed_fields.append(key)

        # List fields: merge deduplicated
        list_keys = ["languages", "preferred_roles"]
        for key in list_keys:
            if key not in fields:
                continue
            new_list = fields[key]
            curr_list = getattr(profile, key, []) or []
            existing_set = {str(item).strip().lower() for item in curr_list}

            to_add = [
                item
                for item in new_list
                if str(item).strip().lower() not in existing_set
            ]
            if to_add:
                setattr(profile, key, curr_list + to_add)
                changed_fields.append(key)

        if changed_fields:
            profile.updated_by_id = actor_id
            profile.updated_at = timezone.now()
            profile.save(update_fields=changed_fields + ["updated_by_id", "updated_at"])
            return True

        return False

    def _sync_skills(
        self, profile: JobSeekerProfile, skills: list[str], *, actor_id: int
    ) -> bool:
        existing_skills = {
            s.skill.name.lower(): s
            for s in JobSeekerSkill.objects.filter(
                job_seeker=profile
            ).select_related("skill")
        }

        added_any = False
        for name in skills:
            clean_name = name.strip()
            if not clean_name:
                continue
            lower_name = clean_name.lower()

            if lower_name in existing_skills:
                link = existing_skills[lower_name]
                if link.is_deleted:
                    link.restore()
                    added_any = True
            else:
                skill_obj, _ = Skill.objects.get_or_create(
                    name=clean_name, defaults={"created_by_id": actor_id}
                )
                JobSeekerSkill.objects.create(
                    job_seeker=profile, skill=skill_obj, created_by_id=actor_id
                )
                added_any = True

        return added_any

    def _sync_experiences(
        self, profile: JobSeekerProfile, experiences: list[dict[str, Any]], *, actor_id: int
    ) -> bool:
        existing = JobSeekerExperience.objects.filter(
            job_seeker=profile, is_deleted=False
        )
        existing_set = {
            (exp.company_name.lower().strip(), exp.title.lower().strip())
            for exp in existing
        }

        created_any = False
        for item in experiences:
            comp = item.get("company_name", "").strip()
            title = item.get("title", "").strip()
            if not comp or not title:
                continue
            key = (comp.lower(), title.lower())
            if key in existing_set:
                continue

            JobSeekerExperience.objects.create(
                job_seeker=profile,
                company_name=comp,
                title=title,
                location=item.get("location") or "",
                start_date=item.get("start_date"),
                end_date=item.get("end_date"),
                is_current=item.get("is_current", False),
                description=item.get("description") or "",
                created_by_id=actor_id,
            )
            existing_set.add(key)
            created_any = True

        return created_any

    def _sync_education(
        self, profile: JobSeekerProfile, education: list[dict[str, Any]], *, actor_id: int
    ) -> bool:
        existing = JobSeekerEducation.objects.filter(
            job_seeker=profile, is_deleted=False
        )
        existing_set = {
            (edu.institution.lower().strip(), edu.degree.lower().strip())
            for edu in existing
        }

        created_any = False
        for item in education:
            inst = item.get("institution", "").strip()
            deg = item.get("degree", "").strip()
            if not inst or not deg:
                continue
            key = (inst.lower(), deg.lower())
            if key in existing_set:
                continue

            JobSeekerEducation.objects.create(
                job_seeker=profile,
                institution=inst,
                degree=deg,
                field_of_study=item.get("field_of_study") or "",
                passing_year=item.get("passing_year"),
                start_year=item.get("start_year"),
                end_year=item.get("end_year"),
                cgpa=item.get("cgpa"),
                percentage=item.get("percentage"),
                created_by_id=actor_id,
            )
            existing_set.add(key)
            created_any = True

        return created_any

    def _sync_projects(
        self, profile: JobSeekerProfile, projects: list[dict[str, Any]], *, actor_id: int
    ) -> bool:
        existing = JobSeekerProject.objects.filter(
            job_seeker=profile, is_deleted=False
        )
        existing_set = {proj.title.lower().strip() for proj in existing}

        created_any = False
        for item in projects:
            title = item.get("title", "").strip()
            if not title:
                continue
            lower_title = title.lower()
            if lower_title in existing_set:
                continue

            JobSeekerProject.objects.create(
                job_seeker=profile,
                title=title,
                description=item.get("description") or "",
                technologies=item.get("technologies") or [],
                project_url=item.get("project_url") or "",
                github_url=item.get("github_url") or "",
                created_by_id=actor_id,
            )
            existing_set.add(lower_title)
            created_any = True

        return created_any

    def _sync_certifications(
        self, profile: JobSeekerProfile, certifications: list[dict[str, Any]], *, actor_id: int
    ) -> bool:
        existing = JobSeekerCertification.objects.filter(
            job_seeker=profile, is_deleted=False
        )
        existing_set = {cert.name.lower().strip() for cert in existing}

        created_any = False
        for item in certifications:
            name = item.get("name", "").strip()
            if not name:
                continue
            lower_name = name.lower()
            if lower_name in existing_set:
                continue

            JobSeekerCertification.objects.create(
                job_seeker=profile,
                name=name,
                issuing_organization=item.get("issuing_organization") or "",
                issue_date=item.get("issue_date"),
                expiry_date=item.get("expiry_date"),
                credential_id=item.get("credential_id") or "",
                credential_url=item.get("credential_url") or "",
                created_by_id=actor_id,
            )
            existing_set.add(lower_name)
            created_any = True

        return created_any
