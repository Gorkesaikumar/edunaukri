"""Job seeker profile page context and section management for the web portal."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from apps.authentication.services.portal_url_service import PortalURLService
from django.urls import reverse
from django.utils.dateparse import parse_date

from apps.accounts.profiles.constants.enums import (
    EmploymentTypePreference,
    Gender,
    ProfileType,
    WorkModePreference,
)
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.documents.constants.enums import StorageFileType
from apps.documents.models import StoredFile
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.constants.education_enums import (
    EDUCATION_LEVEL_ORDER,
    DegreeType,
    EducationBoard,
    EducationLevel,
    EducationScoreType,
    IntermediateStream,
    PGDegreeType,
)
from apps.it_recruitment.models import (
    JobSeekerCertification,
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProfile,
    JobSeekerProject,
)
from apps.it_recruitment.repositories.experience_repository import (
    JobSeekerCertificationRepository,
    JobSeekerEducationRepository,
    JobSeekerExperienceRepository,
    JobSeekerProjectRepository,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_expected_salary_lpa,
    media_url,
    salary_inr_to_lpa_form_value,
    salary_lpa_to_inr,
)
from apps.it_recruitment.services.jobseeker_profile_completion_service import (
    JobSeekerProfileCompletionService,
)
from apps.jobs.constants.enums import EmploymentType
from apps.jobs.models import Skill
from apps.jobs.repositories.seeker_skill_repository import JobSeekerSkillRepository


PROFILE_SELECT_RELATED = ("user", "profile_photo", "resume_file")
PROFILE_PREFETCH = (
    "skills__skill",
    "experiences",
    "education",
    "projects",
    "certifications",
)


@dataclass
class ProfilePageContext:
    profile: JobSeekerProfile
    completion_percentage: int
    completion_status: str
    avatar_url: str | None
    resume_download_url: str | None
    resume_preview_url: str | None
    resume_filename: str | None
    api_urls: dict = field(default_factory=dict)
    choices: dict = field(default_factory=dict)

    def to_template_dict(self) -> dict:
        p = self.profile
        location_parts = [p.city, p.state, p.country]
        location_display = (
            ", ".join(part for part in location_parts if part)
            or p.current_location
            or "—"
        )
        skills = [
            js.skill.name
            for js in p.skills.filter(is_deleted=False).select_related("skill")
            if js.skill_id
        ]
        experiences = list(p.experiences.filter(is_deleted=False))
        education = sorted(
            list(p.education.filter(is_deleted=False)),
            key=lambda e: (
                EDUCATION_LEVEL_ORDER.get(e.education_level, 99),
                -(e.end_year or e.passing_year or 0),
                -(e.start_year or 0),
            ),
        )
        projects = list(p.projects.filter(is_deleted=False))
        certifications = list(p.certifications.filter(is_deleted=False))
        preferred_roles = (
            p.preferred_roles if isinstance(p.preferred_roles, list) else []
        )

        return {
            "profile": p,
            "user_email": p.user.email,
            "full_name": p.full_name,
            "headline": p.headline or "Add a professional headline",
            "current_company": p.current_company,
            "location_display": location_display,
            "experience_display": self._format_experience_years(p.experience_years),
            "completion_percentage": self.completion_percentage,
            "completion_status": self.completion_status,
            "is_profile_verified": bool(
                p.profile_completed and self.completion_percentage >= 100
            ),
            "avatar_url": self.avatar_url,
            "initials": self._initials(p),
            "summary": p.summary,
            "skills": skills,
            "experiences": experiences,
            "education": education,
            "projects": projects,
            "certifications": certifications,
            "preferred_roles": preferred_roles,
            "preferred_roles_display": ", ".join(preferred_roles)
            if preferred_roles
            else "—",
            "preferred_location": p.preferred_location or "—",
            "expected_salary_display": format_expected_salary_lpa(p.expected_salary),
            "employment_type_display": p.get_employment_type_preference_display()
            if p.employment_type_preference
            else "—",
            "work_mode_display": p.get_work_mode_preference_display()
            if p.work_mode_preference
            else "—",
            "notice_period_display": f"{p.notice_period_days} days"
            if p.notice_period_days is not None
            else "—",
            "linkedin_url": p.linkedin_url,
            "github_url": p.github_url,
            "portfolio_url": p.portfolio_url,
            "personal_website": p.personal_website,
            "resume_download_url": self.resume_download_url,
            "resume_preview_url": self.resume_preview_url,
            "resume_filename": self.resume_filename,
            "has_resume": bool(p.resume_file_id),
            "api_urls": self.api_urls,
            "choices": self.choices,
            "gender_display": p.get_gender_display() if p.gender else "—",
            "date_of_birth_display": p.date_of_birth.strftime("%d %b %Y")
            if p.date_of_birth
            else "—",
        }

    @staticmethod
    def _initials(profile: JobSeekerProfile) -> str:
        parts = [profile.first_name[:1], profile.last_name[:1]]
        return "".join(p.upper() for p in parts if p) or "JS"

    @staticmethod
    def _format_experience_years(years) -> str:
        if years is None:
            return "—"
        if years == 0:
            return "Fresher"
        return f"{years} yr{'s' if years != 1 else ''}"


class JobSeekerProfileManageService(BaseService):
    """Orchestrate profile reads and section updates for the job seeker portal."""

    MAX_SUMMARY_LENGTH = 5000

    def __init__(self):
        self.experience_repo = JobSeekerExperienceRepository()
        self.education_repo = JobSeekerEducationRepository()
        self.project_repo = JobSeekerProjectRepository()
        self.certification_repo = JobSeekerCertificationRepository()
        self.skill_repo = JobSeekerSkillRepository()
        self.storage = StorageService()
        self.profile_service = ProfileService()
        self.completion_service = JobSeekerProfileCompletionService()

    def get_profile_queryset(self):
        return (
            JobSeekerProfile.objects.filter(is_deleted=False)
            .select_related(*PROFILE_SELECT_RELATED)
            .prefetch_related(*PROFILE_PREFETCH)
        )

    def get_profile_for_user(self, user) -> JobSeekerProfile:
        profile = self.get_profile_queryset().filter(user=user).first()
        if profile is None:
            raise ResourceNotFoundException("Profile not found.")
        return profile

    def build_page_context(self, profile: JobSeekerProfile) -> ProfilePageContext:
        completion = self.completion_service.get_dashboard_state(profile)
        resume_url = None
        resume_name = None
        if profile.resume_file_id and profile.resume_file:
            resume_url = PortalURLService.jobseeker(
                profile.user, "jobseeker_profile_resume_download"
            )
            resume_name = profile.resume_file.original_filename

        preview_url = None
        if profile.resume_file_id and profile.resume_file:
            ext = (
                profile.resume_file.original_filename.rsplit(".", 1)[-1].lower()
                if profile.resume_file.original_filename
                else ""
            )
            if ext == "pdf":
                preview_url = PortalURLService.jobseeker(
                    profile.user, "jobseeker_profile_resume_preview"
                )

        return ProfilePageContext(
            profile=profile,
            completion_percentage=completion.percentage,
            completion_status=completion.status_label,
            avatar_url=media_url(profile.profile_photo),
            resume_download_url=resume_url,
            resume_preview_url=preview_url,
            resume_filename=resume_name,
            api_urls=self._api_urls(profile.user),
            choices=self._form_choices(),
        )

    def serialize_profile(self, profile: JobSeekerProfile) -> dict:
        """JSON-safe profile payload for the profile page script tag."""
        ctx = self.build_page_context(profile).to_template_dict()
        p = profile
        return {
            "id": str(p.id),
            "first_name": p.first_name,
            "last_name": p.last_name,
            "full_name": ctx["full_name"],
            "headline": p.headline or "",
            "phone": p.phone,
            "gender": p.gender,
            "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            "city": p.city,
            "state": p.state,
            "country": p.country,
            "current_company": p.current_company,
            "current_location": p.current_location,
            "experience_years": p.experience_years,
            "summary": p.summary,
            "preferred_location": p.preferred_location,
            "expected_salary_lpa": salary_inr_to_lpa_form_value(p.expected_salary),
            "expected_salary_display": format_expected_salary_lpa(p.expected_salary),
            "notice_period_days": p.notice_period_days,
            "employment_type_preference": p.employment_type_preference,
            "work_mode_preference": p.work_mode_preference,
            "preferred_roles": p.preferred_roles or [],
            "linkedin_url": p.linkedin_url,
            "github_url": p.github_url,
            "portfolio_url": p.portfolio_url,
            "personal_website": p.personal_website,
            "skills": ctx["skills"],
            "experiences": [
                self._serialize_experience(e)
                for e in p.experiences.filter(is_deleted=False)
            ],
            "education": sorted(
                [
                    self._serialize_education(e)
                    for e in p.education.filter(is_deleted=False)
                ],
                key=lambda item: (
                    EDUCATION_LEVEL_ORDER.get(item.get("education_level"), 99),
                    -(item.get("end_year") or item.get("passing_year") or 0),
                    -(item.get("start_year") or 0),
                ),
            ),
            "projects": [
                self._serialize_project(pj)
                for pj in p.projects.filter(is_deleted=False)
            ],
            "certifications": [
                self._serialize_certification(c)
                for c in p.certifications.filter(is_deleted=False)
            ],
            "completion_percentage": ctx["completion_percentage"],
            "avatar_url": ctx["avatar_url"],
            "api_urls": ctx["api_urls"],
            "choices": ctx["choices"],
            "completion": self.completion_service.get_dashboard_state(
                profile
            ).to_dict(),
        }

    @BaseService.atomic
    def update_section(
        self, profile: JobSeekerProfile, section: str, data: dict, *, actor_id
    ) -> dict:
        handlers = {
            "header": self._update_header,
            "basic": self._update_basic,
            "summary": self._update_summary,
            "skills": self._update_skills,
            "career": self._update_career,
            "social": self._update_social,
        }
        handler = handlers.get(section)
        if not handler:
            raise ValidationException(f"Unknown profile section: {section}")
        handler(profile, data, actor_id)
        profile.refresh_from_db()
        self.completion_service.recalculate(profile)
        from apps.it_recruitment.services.job_recommendation_trigger_service import (
            JobRecommendationTriggerService,
        )

        JobRecommendationTriggerService.after_profile_section(profile.pk, section)
        return self.serialize_profile(profile)

    @BaseService.atomic
    def create_experience(
        self, profile: JobSeekerProfile, data: dict, *, actor_id
    ) -> dict:
        payload = self._parse_experience_payload(data)
        exp = self.experience_repo.create(
            job_seeker=profile, created_by_id=actor_id, **payload
        )
        self.completion_service.recalculate(profile)
        self._trigger_recommendations(profile.pk, "experience_created")
        return self._serialize_experience(exp)

    @BaseService.atomic
    def update_experience(
        self, profile: JobSeekerProfile, exp_id, data: dict, *, actor_id
    ) -> dict:
        exp = self._get_owned_experience(profile, exp_id)
        payload = self._parse_experience_payload(data)
        exp = self.experience_repo.update(exp, updated_by_id=actor_id, **payload)
        self.completion_service.recalculate(profile)
        self._trigger_recommendations(profile.pk, "experience_updated")
        return self._serialize_experience(exp)

    @BaseService.atomic
    def delete_experience(self, profile: JobSeekerProfile, exp_id, *, actor_id) -> None:
        exp = self._get_owned_experience(profile, exp_id)
        exp.delete()
        self.completion_service.recalculate(profile)
        self._trigger_recommendations(profile.pk, "experience_deleted")

    @BaseService.atomic
    def create_education(
        self, profile: JobSeekerProfile, data: dict, *, actor_id
    ) -> dict:
        payload = self._parse_education_payload(data)
        edu = self.education_repo.create(
            job_seeker=profile, created_by_id=actor_id, **payload
        )
        self.completion_service.recalculate(profile)
        self._trigger_recommendations(profile.pk, "education_created")
        return self._serialize_education(edu)

    @BaseService.atomic
    def update_education(
        self, profile: JobSeekerProfile, edu_id, data: dict, *, actor_id
    ) -> dict:
        edu = self._get_owned_education(profile, edu_id)
        payload = self._parse_education_payload(data)
        edu = self.education_repo.update(edu, updated_by_id=actor_id, **payload)
        self.completion_service.recalculate(profile)
        self._trigger_recommendations(profile.pk, "education_updated")
        return self._serialize_education(edu)

    @BaseService.atomic
    def delete_education(self, profile: JobSeekerProfile, edu_id, *, actor_id) -> None:
        edu = self._get_owned_education(profile, edu_id)
        edu.delete()
        self.completion_service.recalculate(profile)
        self._trigger_recommendations(profile.pk, "education_deleted")

    @BaseService.atomic
    def create_project(
        self, profile: JobSeekerProfile, data: dict, *, actor_id
    ) -> dict:
        payload = self._parse_project_payload(data)
        project = self.project_repo.create(
            job_seeker=profile, created_by_id=actor_id, **payload
        )
        self.completion_service.recalculate(profile)
        return self._serialize_project(project)

    @BaseService.atomic
    def update_project(
        self, profile: JobSeekerProfile, project_id, data: dict, *, actor_id
    ) -> dict:
        project = self._get_owned_project(profile, project_id)
        payload = self._parse_project_payload(data)
        project = self.project_repo.update(project, updated_by_id=actor_id, **payload)
        self.completion_service.recalculate(profile)
        return self._serialize_project(project)

    @BaseService.atomic
    def delete_project(
        self, profile: JobSeekerProfile, project_id, *, actor_id
    ) -> None:
        project = self._get_owned_project(profile, project_id)
        project.delete()
        self.completion_service.recalculate(profile)

    @BaseService.atomic
    def create_certification(
        self, profile: JobSeekerProfile, data: dict, *, actor_id
    ) -> dict:
        from apps.it_recruitment.services.certificate_management_service import (
            CertificateManagementService,
        )

        cert = CertificateManagementService().create(
            profile,
            actor_id=actor_id,
            data=data,
            uploaded_file=None,
        )
        return self._serialize_certification(cert)

    @BaseService.atomic
    def update_certification(
        self, profile: JobSeekerProfile, cert_id, data: dict, *, actor_id
    ) -> dict:
        from apps.it_recruitment.services.certificate_management_service import (
            CertificateManagementService,
        )

        cert = CertificateManagementService().update(
            profile, cert_id, actor_id=actor_id, data=data
        )
        return self._serialize_certification(cert)

    @BaseService.atomic
    def delete_certification(
        self, profile: JobSeekerProfile, cert_id, *, actor_id
    ) -> None:
        from apps.it_recruitment.services.certificate_management_service import (
            CertificateManagementService,
        )

        CertificateManagementService().delete(profile, cert_id, actor_id=actor_id)

    @BaseService.atomic
    def upload_resume(
        self, profile: JobSeekerProfile, uploaded_file, *, actor_id
    ) -> dict:
        from django.core.exceptions import ValidationError as DjangoValidationError

        previous_file = profile.resume_file if profile.resume_file_id else None
        try:
            stored = self.storage.upload(
                uploaded_file=uploaded_file,
                domain=DomainType.IT,
                file_type=StorageFileType.RESUME,
                owner_type="job_seeker_profile",
                owner_id=profile.pk,
                uploaded_by_id=actor_id,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise ValidationException(message) from exc

        profile.resume_file = stored
        profile.save(update_fields=["resume_file", "updated_at"])

        from apps.applications.models import JobApplication
        JobApplication.objects.filter(job_seeker=profile, is_deleted=False).update(resume_file=stored)

        if previous_file and previous_file.pk != stored.pk:
            self.storage.remove_stored_file(previous_file)

        from apps.it_recruitment.services.resume_analytics_service import (
            ResumeAnalyticsService,
        )
        from apps.it_recruitment.services.universal_resume_parser import (
            UniversalResumeParserService,
        )
        from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
            JobSeekerResumeAnalysisService,
        )

        ResumeAnalyticsService.init_on_upload(stored, previous=previous_file)
        
        from apps.resume_trust.services.resume_progress_tracker import ResumeProgressTracker
        ResumeProgressTracker.init_tracker(stored.pk)

        self._notify_resume_event(
            profile,
            "resume.uploaded",
            "Resume uploaded",
            "Your resume was uploaded successfully.",
        )
        self._trigger_recommendations(profile.pk, "resume_uploaded")
        self._queue_async_parse(stored.pk, profile.pk)
        
        return self.serialize_profile(profile)

    @staticmethod
    def _queue_async_parse(stored_file_id, profile_id) -> None:
        try:
            from apps.it_recruitment.tasks import parse_resume_task

            parse_resume_task.delay(str(stored_file_id), str(profile_id))
        except Exception:
            pass

    @BaseService.atomic
    def delete_resume(self, profile: JobSeekerProfile, *, actor_id) -> dict:
        previous_file = profile.resume_file if profile.resume_file_id else None
        profile.resume_file = None
        profile.save(update_fields=["resume_file", "updated_at"])
        if previous_file:
            self.storage.remove_stored_file(previous_file)
        self.completion_service.recalculate(profile)
        self._notify_resume_event(
            profile,
            "resume.deleted",
            "Resume deleted",
            "Your resume was removed from your profile.",
        )
        self._trigger_recommendations(profile.pk, "resume_deleted")
        return self.serialize_profile(profile)

    @staticmethod
    def _notify_resume_event(profile, event_type: str, title: str, body: str) -> None:
        from apps.core.constants.enums import DomainType
        from apps.core.services.outbox_service import OutboxService
        from apps.notifications.services.outbox_processor import OutboxProcessorService

        OutboxService().publish(
            domain=DomainType.IT,
            event_type=event_type,
            aggregate_type="job_seeker_profile",
            aggregate_id=profile.pk,
            payload={
                "recipient_domain": "it",
                "recipient_id": str(profile.user_id),
                "title": title,
                "body": body,
            },
        )
        try:
            OutboxProcessorService().process_batch(limit=5)
        except Exception:
            pass

    @BaseService.atomic
    def upload_photo(
        self, profile: JobSeekerProfile, uploaded_file, *, actor_id
    ) -> dict:
        from django.core.exceptions import ValidationError as DjangoValidationError

        try:
            stored = self.storage.upload(
                uploaded_file=uploaded_file,
                domain=DomainType.IT,
                file_type=StorageFileType.PROFILE_PHOTO,
                owner_type="job_seeker_profile",
                owner_id=profile.pk,
                uploaded_by_id=actor_id,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise ValidationException(message) from exc

        profile.profile_photo = stored
        profile.save(update_fields=["profile_photo", "updated_at"])
        self.completion_service.recalculate(profile)
        return self.serialize_profile(profile)

    @BaseService.atomic
    def delete_photo(self, profile: JobSeekerProfile, *, actor_id) -> dict:
        profile.profile_photo = None
        profile.save(update_fields=["profile_photo", "updated_at"])
        self.completion_service.recalculate(profile)
        return self.serialize_profile(profile)

    def get_resume_file(self, profile: JobSeekerProfile) -> StoredFile:
        if not profile.resume_file_id or not profile.resume_file:
            raise ResourceNotFoundException("Resume not found.")
        return profile.resume_file

    @staticmethod
    def _trigger_recommendations(profile_id, reason: str) -> None:
        from apps.it_recruitment.services.job_recommendation_trigger_service import (
            JobRecommendationTriggerService,
        )

        JobRecommendationTriggerService.after_profile_mutation(
            profile_id, reason=reason
        )

    def _api_urls(self, user) -> dict:
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        placeholder = "00000000-0000-0000-0000-000000000000"
        return {
            "profile": pu("jobseeker_profile_api"),
            "section": pu("jobseeker_profile_section_api", section="__section__"),
            "experiences": pu("jobseeker_profile_experiences_api"),
            "experience_detail": pu(
                "jobseeker_profile_experience_detail_api", experience_id=placeholder
            ).replace(placeholder, "__id__"),
            "education": pu("jobseeker_profile_education_api"),
            "education_detail": pu(
                "jobseeker_profile_education_detail_api", education_id=placeholder
            ).replace(placeholder, "__id__"),
            "projects": pu("jobseeker_profile_projects_api"),
            "project_detail": pu(
                "jobseeker_profile_project_detail_api", project_id=placeholder
            ).replace(placeholder, "__id__"),
            "certifications": pu("jobseeker_profile_certifications_api"),
            "certification_detail": pu(
                "jobseeker_profile_certification_detail_api",
                certification_id=placeholder,
            ).replace(placeholder, "__id__"),
            "resume_upload": pu("jobseeker_profile_resume_api"),
            "resume_download": pu("jobseeker_profile_resume_download"),
            "resume_preview": pu("jobseeker_profile_resume_preview"),
            "photo_upload": pu("jobseeker_profile_photo_api"),
            "recommendations": pu("jobseeker_recommendations_api"),
        }

    def _form_choices(self) -> dict:
        return {
            "gender": [{"value": c[0], "label": c[1]} for c in Gender.choices],
            "employment_type": [
                {"value": c[0], "label": c[1]} for c in EmploymentType.choices
            ],
            "employment_type_preference": [
                {"value": c[0], "label": c[1]} for c in EmploymentTypePreference.choices
            ],
            "work_mode_preference": [
                {"value": c[0], "label": c[1]} for c in WorkModePreference.choices
            ],
            "education_level": [
                {"value": c[0], "label": c[1]} for c in EducationLevel.choices
            ],
            "education_board": [
                {"value": c[0], "label": c[1]} for c in EducationBoard.choices
            ],
            "intermediate_stream": [
                {"value": c[0], "label": c[1]} for c in IntermediateStream.choices
            ],
            "degree_type": [{"value": c[0], "label": c[1]} for c in DegreeType.choices],
            "pg_degree_type": [
                {"value": c[0], "label": c[1]} for c in PGDegreeType.choices
            ],
            "education_score_type": [
                {"value": c[0], "label": c[1]} for c in EducationScoreType.choices
            ],
        }

    def _parse_optional_date(self, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            parsed = parse_date(value)
            if parsed is None:
                raise ValidationException("Enter a valid date of birth.")
            return parsed
        return value

    @staticmethod
    def _strip(value):
        return value.strip() if isinstance(value, str) else value

    def _update_header(self, profile: JobSeekerProfile, data: dict, actor_id) -> None:
        first_name = self._strip(data.get("first_name"))
        if first_name is not None and not first_name:
            raise ValidationException("First name is required.")

        last_name = self._strip(data.get("last_name"))
        if last_name is None:
            last_name = profile.last_name or ""

        headline = self._strip(data.get("headline"))
        if headline is None:
            headline = profile.headline or ""

        current_company = self._strip(data.get("current_company"))
        if current_company is None:
            current_company = profile.current_company or ""

        current_location = self._strip(data.get("current_location"))
        if current_location is None:
            current_location = profile.current_location or ""

        exp_years_raw = data.get("experience_years")
        if exp_years_raw == "" or exp_years_raw is None:
            exp_years = None if "experience_years" in data else profile.experience_years
        else:
            exp_years = self._optional_int(exp_years_raw)

        payload = {
            "first_name": first_name if first_name is not None else profile.first_name,
            "last_name": last_name,
            "headline": headline,
            "current_company": current_company,
            "current_location": current_location,
            "experience_years": exp_years,
        }
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.JOB_SEEKER,
            data=payload,
        )

    def _update_basic(self, profile: JobSeekerProfile, data: dict, actor_id) -> None:
        if "first_name" in data:
            fn = self._strip(data["first_name"])
            if not fn:
                raise ValidationException("First name is required.")
        parsed_dob = (
            self._parse_optional_date(data.get("date_of_birth"))
            if "date_of_birth" in data
            else None
        )
        if parsed_dob and parsed_dob > date.today():
            raise ValidationException("Date of birth cannot be in the future.")
        payload: dict = {}
        for field in (
            "first_name",
            "last_name",
            "phone",
            "gender",
            "city",
            "state",
            "country",
        ):
            if field in data:
                payload[field] = self._strip(data[field]) or ""
        if "date_of_birth" in data:
            payload["date_of_birth"] = parsed_dob
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.JOB_SEEKER,
            data=payload,
        )

    def _update_summary(self, profile: JobSeekerProfile, data: dict, actor_id) -> None:
        summary = (data.get("summary") or "").strip()
        if len(summary) > self.MAX_SUMMARY_LENGTH:
            raise ValidationException(
                f"Summary cannot exceed {self.MAX_SUMMARY_LENGTH} characters."
            )
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.JOB_SEEKER,
            data={"summary": summary},
        )

    def _update_skills(self, profile: JobSeekerProfile, data: dict, actor_id) -> None:
        raw = data.get("skills") or []
        if isinstance(raw, str):
            raw = [s.strip() for s in raw.split(",") if s.strip()]
        seen: set[str] = set()
        cleaned: list[str] = []
        for item in raw:
            name = str(item).strip()
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            cleaned.append(name)
        if len(cleaned) > 50:
            raise ValidationException("You can add up to 50 skills.")
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.JOB_SEEKER,
            data={"skills": cleaned},
        )

    def _update_career(self, profile: JobSeekerProfile, data: dict, actor_id) -> None:
        roles = data.get("preferred_roles") or []
        if isinstance(roles, str):
            roles = [r.strip() for r in roles.split(",") if r.strip()]
        if len(roles) > 20:
            raise ValidationException("You can add up to 20 preferred roles.")
        payload: dict = {"preferred_roles": roles}
        for field in (
            "preferred_location",
            "employment_type_preference",
            "work_mode_preference",
        ):
            if field in data:
                payload[field] = self._strip(data[field])
        if "expected_salary" in data:
            if data["expected_salary"] in (None, ""):
                payload["expected_salary"] = None
            else:
                try:
                    payload["expected_salary"] = salary_lpa_to_inr(
                        data["expected_salary"]
                    )
                except ValueError as exc:
                    raise ValidationException(str(exc)) from exc
        if "notice_period_days" in data:
            if data["notice_period_days"] in (None, ""):
                payload["notice_period_days"] = None
            else:
                notice = self._optional_int(data["notice_period_days"])
                if notice is None or notice < 0 or notice > 365:
                    raise ValidationException(
                        "Notice period must be between 0 and 365 days."
                    )
                payload["notice_period_days"] = notice
        if (
            payload.get("employment_type_preference")
            and payload["employment_type_preference"]
            not in EmploymentTypePreference.values
        ):
            raise ValidationException("Select a valid employment type preference.")
        if (
            payload.get("work_mode_preference")
            and payload["work_mode_preference"] not in WorkModePreference.values
        ):
            raise ValidationException("Select a valid work mode preference.")
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.JOB_SEEKER,
            data=payload,
        )

    def _update_social(self, profile: JobSeekerProfile, data: dict, actor_id) -> None:
        payload = {
            field: self._strip(data[field])
            for field in (
                "linkedin_url",
                "github_url",
                "portfolio_url",
                "personal_website",
            )
            if field in data
        }
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.JOB_SEEKER,
            data=payload,
        )

    def _parse_experience_payload(self, data: dict) -> dict:
        company_name = (data.get("company_name") or "").strip()
        title = (data.get("title") or "").strip()
        if not company_name or not title:
            raise ValidationException("Company name and designation are required.")
        start = parse_date(data["start_date"]) if data.get("start_date") else None
        end = parse_date(data["end_date"]) if data.get("end_date") else None
        is_current = bool(data.get("is_current"))
        if start and end and not is_current and end < start:
            raise ValidationException("Experience end date must be after start date.")
        emp_type = data.get("employment_type") or EmploymentType.FULL_TIME
        if emp_type not in EmploymentType.values:
            raise ValidationException("Invalid employment type.")
        return {
            "company_name": company_name,
            "title": title,
            "employment_type": emp_type,
            "location": (data.get("location") or "").strip(),
            "start_date": start,
            "end_date": None if is_current else end,
            "is_current": is_current,
            "description": (data.get("description") or "").strip(),
        }

    def _parse_education_payload(self, data: dict) -> dict:
        level = (data.get("education_level") or "").strip()
        if level not in EducationLevel.values:
            raise ValidationException("Select a valid education level.")

        score_type = (data.get("score_type") or "").strip()
        if score_type and score_type not in EducationScoreType.values:
            raise ValidationException("Select Percentage or CGPA.")
        percentage, cgpa = self._parse_education_score(score_type, data)

        current_year = date.today().year
        payload: dict = {
            "education_level": level,
            "score_type": score_type,
            "percentage": percentage,
            "cgpa": cgpa,
            "board": (data.get("board") or "").strip(),
            "stream": (data.get("stream") or "").strip(),
            "degree_type": (data.get("degree_type") or "").strip(),
            "field_of_study": (
                data.get("field_of_study") or data.get("specialization") or ""
            ).strip(),
            "grade": (data.get("grade") or "").strip(),
        }

        if level == EducationLevel.SCHOOL:
            school_name = (
                data.get("school_name") or data.get("institution") or ""
            ).strip()
            if not school_name:
                raise ValidationException("School name is required.")
            if not payload["board"]:
                raise ValidationException("Board is required.")
            passing_year = self._optional_int(
                data.get("passing_year") or data.get("end_year")
            )
            self._validate_passing_year(passing_year, current_year)
            payload.update(
                {
                    "institution": school_name,
                    "university": "",
                    "college": "",
                    "degree": "SSC / 10th",
                    "passing_year": passing_year,
                    "end_year": passing_year,
                    "start_year": None,
                    "stream": "",
                    "degree_type": "",
                }
            )
        elif level == EducationLevel.INTERMEDIATE:
            college_name = (
                data.get("college") or data.get("institution") or ""
            ).strip()
            board_university = (
                data.get("university") or data.get("board_university") or ""
            ).strip()
            if not college_name:
                raise ValidationException("Intermediate college name is required.")
            if not board_university and not payload["board"]:
                raise ValidationException("Board or university is required.")
            if not payload["stream"]:
                raise ValidationException("Stream is required.")
            passing_year = self._optional_int(
                data.get("passing_year") or data.get("end_year")
            )
            self._validate_passing_year(passing_year, current_year)
            degree_label = (
                "Diploma"
                if payload["stream"] == IntermediateStream.DIPLOMA
                else "Intermediate (12th)"
            )
            payload.update(
                {
                    "institution": college_name,
                    "college": college_name,
                    "university": board_university,
                    "degree": degree_label,
                    "passing_year": passing_year,
                    "end_year": passing_year,
                    "start_year": None,
                    "degree_type": "",
                }
            )
        elif level == EducationLevel.DEGREE:
            degree_type = payload["degree_type"]
            if not degree_type:
                raise ValidationException("Degree type is required.")
            college_name = (data.get("college") or "").strip()
            university = (data.get("university") or "").strip()
            if not college_name:
                raise ValidationException("College name is required.")
            if not university:
                raise ValidationException("University is required.")
            start_year = self._optional_int(data.get("start_year"))
            end_year = self._optional_int(data.get("end_year"))
            self._validate_year_range(start_year, end_year, current_year)
            payload.update(
                {
                    "institution": college_name,
                    "college": college_name,
                    "university": university,
                    "degree": self._degree_type_label(degree_type, DegreeType.choices),
                    "start_year": start_year,
                    "end_year": end_year,
                    "passing_year": None,
                    "board": "",
                    "stream": "",
                }
            )
        elif level == EducationLevel.POST_GRADUATION:
            degree_type = payload["degree_type"]
            if not degree_type:
                raise ValidationException("PG degree is required.")
            institution = (
                data.get("institution")
                or data.get("college")
                or data.get("college_university")
                or ""
            ).strip()
            if not institution:
                raise ValidationException("College or university name is required.")
            start_year = self._optional_int(data.get("start_year"))
            end_year = self._optional_int(data.get("end_year"))
            self._validate_year_range(start_year, end_year, current_year)
            payload.update(
                {
                    "institution": institution,
                    "college": institution,
                    "university": (data.get("university") or "").strip(),
                    "degree": self._degree_type_label(
                        degree_type, PGDegreeType.choices
                    ),
                    "start_year": start_year,
                    "end_year": end_year,
                    "passing_year": None,
                    "board": "",
                    "stream": "",
                }
            )
        else:
            raise ValidationException("Unsupported education level.")

        return payload

    def _parse_education_score(self, score_type: str, data: dict) -> tuple:
        if not score_type:
            raise ValidationException("Select Percentage or CGPA.")
        if score_type == EducationScoreType.PERCENTAGE:
            percentage = self._optional_decimal(data.get("percentage"), max_digits=5)
            if percentage is None:
                raise ValidationException("Percentage is required.")
            if percentage < 0 or percentage > 100:
                raise ValidationException("Percentage must be between 0 and 100.")
            return percentage, None
        cgpa = self._optional_decimal(data.get("cgpa"), max_digits=4)
        if cgpa is None:
            raise ValidationException("CGPA is required.")
        if cgpa < 0 or cgpa > 10:
            raise ValidationException("CGPA must be between 0 and 10.")
        return None, cgpa

    @staticmethod
    def _validate_passing_year(year: int | None, current_year: int) -> None:
        if year is None:
            raise ValidationException("Passing year is required.")
        if year < 1970 or year > current_year:
            raise ValidationException("Passing year cannot be in the future.")

    @staticmethod
    def _validate_year_range(
        start_year: int | None, end_year: int | None, current_year: int
    ) -> None:
        if start_year is None or end_year is None:
            raise ValidationException("Start year and end year are required.")
        if start_year < 1970 or end_year < 1970:
            raise ValidationException("Enter a valid year.")
        if end_year > current_year + 1:
            raise ValidationException("End year cannot be in the future.")
        if end_year < start_year:
            raise ValidationException(
                "End year must be greater than or equal to start year."
            )

    @staticmethod
    def _degree_type_label(value: str, choices) -> str:
        for choice_value, choice_label in choices:
            if choice_value == value:
                return choice_label
        return value.replace("_", " ").title()

    def _parse_project_payload(self, data: dict) -> dict:
        title = (data.get("title") or "").strip()
        if not title:
            raise ValidationException("Project title is required.")
        tech = data.get("technologies") or data.get("technology_used") or []
        if isinstance(tech, str):
            tech = [t.strip() for t in tech.split(",") if t.strip()]
        return {
            "title": title,
            "description": (data.get("description") or "").strip(),
            "technologies": tech,
            "project_url": (data.get("project_url") or "").strip(),
            "github_url": (data.get("github_url") or "").strip(),
        }

    def _parse_certification_payload(self, data: dict) -> dict:
        issue = parse_date(data["issue_date"]) if data.get("issue_date") else None
        expiry = parse_date(data["expiry_date"]) if data.get("expiry_date") else None
        name = (data.get("name") or data.get("certification_name") or "").strip()
        if not name:
            raise ValidationException("Certification name is required.")
        org = (
            data.get("issuing_organization") or data.get("organization") or ""
        ).strip()
        cat = (data.get("category") or "other").strip().lower()
        return {
            "name": name,
            "issuing_organization": org,
            "category": cat,
            "issue_date": issue,
            "expiry_date": expiry,
            "credential_id": (data.get("credential_id") or "").strip(),
            "credential_url": (data.get("credential_url") or "").strip(),
        }

    def _get_owned_experience(self, profile, exp_id) -> JobSeekerExperience:
        exp = profile.experiences.filter(pk=exp_id, is_deleted=False).first()
        if not exp:
            raise ResourceNotFoundException("Experience record not found.")
        return exp

    def _get_owned_education(self, profile, edu_id) -> JobSeekerEducation:
        edu = profile.education.filter(pk=edu_id, is_deleted=False).first()
        if not edu:
            raise ResourceNotFoundException("Education record not found.")
        return edu

    def _get_owned_project(self, profile, project_id) -> JobSeekerProject:
        project = profile.projects.filter(pk=project_id, is_deleted=False).first()
        if not project:
            raise ResourceNotFoundException("Project not found.")
        return project

    def _get_owned_certification(self, profile, cert_id) -> JobSeekerCertification:
        cert = profile.certifications.filter(pk=cert_id, is_deleted=False).first()
        if not cert:
            raise ResourceNotFoundException("Certification not found.")
        return cert

    @staticmethod
    def _optional_int(value):
        if value in (None, ""):
            return None
        return int(value)

    @staticmethod
    def _optional_decimal(value, *, max_digits: int):
        if value in (None, ""):
            return None
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationException("Invalid numeric value.") from exc
        if dec < 0:
            raise ValidationException("Numeric values cannot be negative.")
        return dec

    @staticmethod
    def _serialize_experience(exp: JobSeekerExperience) -> dict:
        return {
            "id": str(exp.id),
            "company_name": exp.company_name,
            "title": exp.title,
            "employment_type": exp.employment_type,
            "employment_type_display": exp.get_employment_type_display(),
            "location": exp.location,
            "start_date": exp.start_date.isoformat() if exp.start_date else None,
            "end_date": exp.end_date.isoformat() if exp.end_date else None,
            "is_current": exp.is_current,
            "description": exp.description,
        }

    @staticmethod
    def _serialize_education(edu: JobSeekerEducation) -> dict:
        return {
            "id": str(edu.id),
            "education_level": edu.education_level,
            "education_level_label": edu.level_label,
            "institution": edu.institution,
            "school_name": edu.institution
            if edu.education_level == EducationLevel.SCHOOL
            else "",
            "university": edu.university,
            "college": edu.college,
            "board": edu.board,
            "board_display": edu.get_board_display() if edu.board else "",
            "stream": edu.stream,
            "stream_display": edu.get_stream_display() if edu.stream else "",
            "degree_type": edu.degree_type,
            "score_type": edu.score_type,
            "degree": edu.degree,
            "field_of_study": edu.field_of_study,
            "specialization": edu.field_of_study,
            "percentage": str(edu.percentage) if edu.percentage is not None else None,
            "cgpa": str(edu.cgpa) if edu.cgpa is not None else None,
            "passing_year": edu.passing_year,
            "start_year": edu.start_year,
            "end_year": edu.end_year,
            "grade": edu.grade,
            "score_display": edu.score_display,
            "year_display": edu.year_display,
        }

    @staticmethod
    def _serialize_project(project: JobSeekerProject) -> dict:
        return {
            "id": str(project.id),
            "title": project.title,
            "description": project.description,
            "technologies": project.technologies or [],
            "project_url": project.project_url,
            "github_url": project.github_url,
        }

    @staticmethod
    def _serialize_certification(cert: JobSeekerCertification) -> dict:
        from apps.it_recruitment.services.certificate_management_service import (
            CertificateManagementService,
        )

        status = CertificateManagementService.resolve_status(cert)
        return {
            "id": str(cert.id),
            "name": cert.name,
            "issuing_organization": cert.issuing_organization,
            "category": cert.category,
            "issue_date": cert.issue_date.isoformat() if cert.issue_date else None,
            "expiry_date": cert.expiry_date.isoformat() if cert.expiry_date else None,
            "credential_id": cert.credential_id,
            "credential_url": cert.credential_url,
            "is_verified": cert.is_verified,
            "has_file": bool(cert.certificate_file_id),
            "status_key": status.key,
            "status_label": status.label,
        }
