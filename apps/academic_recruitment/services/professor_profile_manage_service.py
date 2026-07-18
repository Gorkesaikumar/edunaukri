"""Professor profile page management for the web portal."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse

from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.services.profile_completion_service import (
    ProfileCompletionService,
)
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.academic_recruitment.models import (
    ProfessorProfile,
    ProfessorQualification,
    Qualification,
)
from apps.academic_recruitment.services.professor_portal_helpers import (
    initials_from_name,
    media_url,
)
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.services.base import BaseService
from apps.documents.constants.enums import StorageFileType
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_expected_salary_lpa,
    salary_inr_to_lpa_form_value,
    salary_lpa_to_inr,
)


PROFILE_SELECT = ("user", "profile_photo", "cv_file")
PROFILE_PREFETCH = ("qualifications__qualification", "departments__department")


@dataclass
class ProfessorProfilePageContext:
    profile: ProfessorProfile
    completion_percentage: int
    completion_status: str
    avatar_url: str | None
    cv_filename: str | None
    api_urls: dict = field(default_factory=dict)

    def to_template_dict(self) -> dict:
        p = self.profile
        pu = lambda name, **kw: PortalURLService.professor(p.user, name, **kw)
        qualifications = [
            {
                "id": str(row.id),
                "name": row.qualification.name,
                "institution_name": row.institution_name,
                "year_obtained": row.year_obtained,
                "has_certificate": row.certificate_file_id is not None,
            }
            for row in p.qualifications.filter(is_deleted=False).select_related(
                "qualification"
            )
        ]
        departments = [
            row.department.name
            for row in p.departments.filter(is_deleted=False).select_related(
                "department"
            )
            if row.department_id
        ]
        preferred = (
            ", ".join(str(loc) for loc in (p.preferred_locations or []) if loc) or "—"
        )
        exp_parts = []
        if p.teaching_experience_years is not None:
            exp_parts.append(f"{p.teaching_experience_years} yrs teaching")
        if p.industry_experience_years is not None:
            exp_parts.append(f"{p.industry_experience_years} yrs industry")
        elif p.experience_years is not None:
            exp_parts.append(f"{p.experience_years} yrs total")

        return {
            "first_name": p.first_name,
            "last_name": p.last_name,
            "full_name": p.full_name,
            "initials": initials_from_name(p.full_name, p.user.email[:2]),
            "user_email": p.user.email,
            "headline": p.current_designation
            or p.specialization
            or "Faculty Job Seeker",
            "avatar_url": self.avatar_url,
            "cv_filename": self.cv_filename,
            "completion_percentage": self.completion_percentage,
            "completion_status": self.completion_status,
            "specialization": p.specialization or "",
            "research_interests": p.research_interests or "",
            "highest_qualification": p.highest_qualification or "",
            "current_designation": p.current_designation or "",
            "current_institution": p.current_institution or "",
            "publications_count": p.publications_count or 0,
            "teaching_experience_years": p.teaching_experience_years,
            "industry_experience_years": p.industry_experience_years,
            "experience_years": p.experience_years,
            "experience_display": " • ".join(exp_parts) if exp_parts else "—",
            "expected_salary_display": format_expected_salary_lpa(p.expected_salary)
            if p.expected_salary
            else "—",
            "expected_salary_lpa": salary_inr_to_lpa_form_value(p.expected_salary)
            if p.expected_salary
            else "",
            "preferred_locations_display": preferred,
            "preferred_locations": p.preferred_locations or [],
            "qualifications": qualifications,
            "departments": departments,
            "phone": p.phone or "",
            "completion": ProfessorProfileCompletionService()
            .get_dashboard_state(p)
            .to_dict(),
            "api_urls": self.api_urls,
        }


class ProfessorProfileManageService(BaseService):
    def __init__(self):
        self.profile_service = ProfileService()
        self.completion_service = ProfileCompletionService()
        self.storage = StorageService()

    def get_profile_queryset(self):
        return (
            ProfessorProfile.objects.filter(is_deleted=False)
            .select_related(*PROFILE_SELECT)
            .prefetch_related(*PROFILE_PREFETCH)
        )

    def get_profile_for_user(self, user) -> ProfessorProfile:
        profile = self.get_profile_queryset().filter(user=user).first()
        if not profile:
            raise ResourceNotFoundException("Professor profile not found.")
        return profile

    def build_page_context(
        self, profile: ProfessorProfile
    ) -> ProfessorProfilePageContext:
        percentage = self.completion_service.calculate(profile, ProfileType.PROFESSOR)
        pu = lambda name, **kw: PortalURLService.professor(profile.user, name, **kw)
        cv_name = None
        if profile.cv_file_id and profile.cv_file:
            cv_name = (
                profile.cv_file.original_filename
                or profile.cv_file.file.name.split("/")[-1]
            )

        return ProfessorProfilePageContext(
            profile=profile,
            completion_percentage=percentage,
            completion_status=ProfessorProfileCompletionService()
            .get_dashboard_state(profile)
            .status_label,
            avatar_url=media_url(profile.profile_photo),
            cv_filename=cv_name,
            api_urls={
                "profile": pu("professor_profile_api"),
                "section": pu(
                    "professor_profile_section_api", section="__SECTION__"
                ).replace("__SECTION__", "{section}"),
                "photo": pu("professor_profile_photo_api"),
                "cv": pu("professor_profile_cv_api"),
                "qualifications": pu("professor_profile_qualifications_api"),
            },
        )

    def serialize_profile(self, profile: ProfessorProfile) -> dict:
        return self.build_page_context(profile).to_template_dict()

    @BaseService.atomic
    def update_section(
        self, profile: ProfessorProfile, section: str, data: dict, *, actor_id
    ) -> dict:
        payload = self._section_payload(section, data)
        if not payload:
            raise ValidationException(f"Unknown profile section: {section}")
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.PROFESSOR,
            data=payload,
        )
        profile.refresh_from_db()
        ProfileCompletionService().calculate(profile, ProfileType.PROFESSOR)
        return self.serialize_profile(profile)

    @BaseService.atomic
    def upload_photo(
        self, profile: ProfessorProfile, uploaded_file, *, actor_id
    ) -> dict:
        previous_file = profile.profile_photo if profile.profile_photo_id else None
        try:
            stored = self.storage.upload(
                uploaded_file=uploaded_file,
                domain=DomainType.FACULTY,
                file_type=StorageFileType.PROFILE_PHOTO,
                owner_type="professor_profile",
                owner_id=profile.pk,
                uploaded_by_id=actor_id,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise ValidationException(message) from exc

        profile.profile_photo = stored
        profile.save(update_fields=["profile_photo", "updated_at"])
        if previous_file and previous_file.pk != stored.pk:
            self.storage.remove_stored_file(previous_file)
        self.completion_service.calculate(profile, ProfileType.PROFESSOR)
        return self.serialize_profile(profile)

    @BaseService.atomic
    def upload_cv(self, profile: ProfessorProfile, uploaded_file, *, actor_id) -> dict:
        previous_file = profile.cv_file if profile.cv_file_id else None
        try:
            stored = self.storage.upload(
                uploaded_file=uploaded_file,
                domain=DomainType.FACULTY,
                file_type=StorageFileType.CV,
                owner_type="professor_profile",
                owner_id=profile.pk,
                uploaded_by_id=actor_id,
            )
        except DjangoValidationError as exc:
            message = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            raise ValidationException(message) from exc

        profile.cv_file = stored
        profile.save(update_fields=["cv_file", "updated_at"])
        if previous_file and previous_file.pk != stored.pk:
            self.storage.remove_stored_file(previous_file)
        self.completion_service.calculate(profile, ProfileType.PROFESSOR)
        
        # Trigger background parsing task
        from apps.academic_recruitment.tasks import parse_faculty_resume_task
        parse_faculty_resume_task.delay(profile.pk, stored.pk)
        
        return self.serialize_profile(profile)

    @BaseService.atomic
    def delete_cv(self, profile: ProfessorProfile, *, actor_id) -> dict:
        previous = profile.cv_file if profile.cv_file_id else None
        self.profile_service.update_profile(
            user=profile.user,
            profile_type=ProfileType.PROFESSOR,
            data={"cv_file_id": None},
        )
        if previous:
            self.storage.remove_stored_file(previous)
        profile.refresh_from_db()
        return self.serialize_profile(profile)

    def get_cv_file(self, profile: ProfessorProfile):
        if not profile.cv_file_id or not profile.cv_file:
            raise ResourceNotFoundException("CV not found.")
        return profile.cv_file

    def _section_payload(self, section: str, data: dict) -> dict:
        if section == "basic":
            return {
                k: (data.get(k) or "").strip()
                for k in ("first_name", "last_name", "phone")
                if k in data
            }
        if section == "professional":
            payload = {}
            for key in (
                "current_designation",
                "current_institution",
                "highest_qualification",
                "specialization",
            ):
                if key in data:
                    payload[key] = (data.get(key) or "").strip()
            for key in (
                "teaching_experience_years",
                "industry_experience_years",
                "experience_years",
                "publications_count",
            ):
                if key in data and data[key] not in (None, ""):
                    payload[key] = int(data[key])
            if "expected_salary_lpa" in data:
                lpa = data.get("expected_salary_lpa")
                if lpa in (None, ""):
                    payload["expected_salary"] = None
                else:
                    try:
                        payload["expected_salary"] = salary_lpa_to_inr(
                            Decimal(str(lpa))
                        )
                    except (InvalidOperation, ValueError) as exc:
                        raise ValidationException("Invalid expected salary.") from exc
            return payload
        if section == "research":
            payload = {}
            if "research_interests" in data:
                payload["research_interests"] = data.get("research_interests") or ""
            if "publications_count" in data and data["publications_count"] not in (
                None,
                "",
            ):
                payload["publications_count"] = int(data["publications_count"])
            return payload
        if section == "locations":
            raw = data.get("preferred_locations")
            if isinstance(raw, str):
                locations = [part.strip() for part in raw.split(",") if part.strip()]
            elif isinstance(raw, list):
                locations = [str(part).strip() for part in raw if str(part).strip()]
            else:
                locations = []
            return {"preferred_locations": locations}
        return {}

    @staticmethod
    def _serialize_qualification(row: ProfessorQualification) -> dict:
        return {
            "id": str(row.id),
            "name": row.qualification.name,
            "institution_name": row.institution_name,
            "year_obtained": row.year_obtained,
            "has_certificate": row.certificate_file_id is not None,
        }

    @BaseService.atomic
    def create_qualification(
        self, profile: ProfessorProfile, data: dict, *, actor_id
    ) -> dict:
        name = (data.get("name") or data.get("qualification_name") or "").strip()
        if not name:
            raise ValidationException("Qualification name is required.")
        qualification, _ = Qualification.objects.get_or_create(
            name=name,
            defaults={"created_by_id": actor_id},
        )
        year = data.get("year_obtained")
        if year in (None, ""):
            year_val = None
        else:
            try:
                year_val = int(year)
            except (TypeError, ValueError) as exc:
                raise ValidationException(
                    "Year obtained must be a valid year."
                ) from exc
        row = ProfessorQualification.objects.create(
            professor=profile,
            qualification=qualification,
            institution_name=(data.get("institution_name") or "").strip(),
            year_obtained=year_val,
            created_by_id=actor_id,
        )
        ProfileCompletionService().calculate(profile, ProfileType.PROFESSOR)
        return self._serialize_qualification(row)

    @BaseService.atomic
    def update_qualification(
        self, profile: ProfessorProfile, qualification_id, data: dict, *, actor_id
    ) -> dict:
        row = (
            profile.qualifications.filter(pk=qualification_id, is_deleted=False)
            .select_related("qualification")
            .first()
        )
        if not row:
            raise ResourceNotFoundException("Qualification not found.")
        if "name" in data or "qualification_name" in data:
            name = (data.get("name") or data.get("qualification_name") or "").strip()
            if not name:
                raise ValidationException("Qualification name is required.")
            qualification, _ = Qualification.objects.get_or_create(
                name=name,
                defaults={"created_by_id": actor_id},
            )
            row.qualification = qualification
        if "institution_name" in data:
            row.institution_name = (data.get("institution_name") or "").strip()
        if "year_obtained" in data:
            year = data.get("year_obtained")
            if year in (None, ""):
                row.year_obtained = None
            else:
                try:
                    row.year_obtained = int(year)
                except (TypeError, ValueError) as exc:
                    raise ValidationException(
                        "Year obtained must be a valid year."
                    ) from exc
        row.updated_by_id = actor_id
        row.save()
        ProfileCompletionService().calculate(profile, ProfileType.PROFESSOR)
        return self._serialize_qualification(row)

    @BaseService.atomic
    def delete_qualification(
        self, profile: ProfessorProfile, qualification_id, *, actor_id
    ) -> None:
        row = profile.qualifications.filter(
            pk=qualification_id, is_deleted=False
        ).first()
        if not row:
            raise ResourceNotFoundException("Qualification not found.")
        row.is_deleted = True
        row.updated_by_id = actor_id
        row.save(update_fields=["is_deleted", "updated_by_id", "updated_at"])
        ProfileCompletionService().calculate(profile, ProfileType.PROFESSOR)
