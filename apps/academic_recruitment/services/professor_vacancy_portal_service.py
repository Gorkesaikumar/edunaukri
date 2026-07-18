"""Faculty vacancy detail page for the professor portal."""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_portal_helpers import (
    institution_profile_url,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import SalaryVisibility
from apps.faculty.models import FacultyVacancy
from apps.faculty.services.saved_vacancy_service import SavedVacancyService
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    media_url,
)


@dataclass
class VacancyDetailSection:
    key: str
    title: str
    content: str


@dataclass
class ProfessorVacancyDetailContext:
    id: str
    title: str
    institution_name: str
    location: str
    logo_url: str | None
    tags: list[str]
    meta: list[tuple[str, str]]
    sections: list[VacancyDetailSection]
    is_saved: bool
    has_applied: bool
    application_status: str | None
    apply_url: str
    save_url: str
    browse_url: str
    posted_display: str
    deadline_display: str | None
    application_detail_url: str | None = None
    institution_url: str | None = None
    is_eligible: bool = True
    eligibility_message: str = ""

    def to_template_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "institution_name": self.institution_name,
            "location": self.location,
            "logo_url": self.logo_url,
            "tags": self.tags,
            "meta": [{"label": label, "value": value} for label, value in self.meta],
            "sections": [
                {"key": s.key, "title": s.title, "content": s.content}
                for s in self.sections
            ],
            "is_saved": self.is_saved,
            "has_applied": self.has_applied,
            "application_status": self.application_status,
            "apply_url": self.apply_url,
            "save_url": self.save_url,
            "browse_url": self.browse_url,
            "posted_display": self.posted_display,
            "deadline_display": self.deadline_display,
            "application_detail_url": self.application_detail_url,
            "institution_url": self.institution_url,
            "is_eligible": self.is_eligible,
            "eligibility_message": self.eligibility_message,
        }


class ProfessorVacancyPortalService(BaseService):
    def build_detail(
        self, profile: ProfessorProfile | None, vacancy: FacultyVacancy
    ) -> ProfessorVacancyDetailContext:
        user = profile.user if profile else None
        pu = lambda name, **kw: (
            PortalURLService.professor(user, name, **kw) if user else ""
        )

        college = vacancy.college if vacancy.college_id else None
        logo = (
            media_url(college.logo_file) if college and college.logo_file_id else None
        )
        location = self._location(vacancy)
        tags = self._tags(vacancy)
        meta = self._meta_rows(vacancy)

        saved_ids = (
            SavedVacancyService().status_map(profile, [str(vacancy.pk)])
            if profile
            else {}
        )
        application = None
        is_eligible = True
        eligibility_message = ""
        if profile:
            application = (
                profile.applications.filter(vacancy=vacancy, is_deleted=False)
                .order_by("-created_at")
                .first()
            )
            from apps.academic_recruitment.services.faculty_application_eligibility_service import FacultyApplicationEligibilityService
            eligibility = FacultyApplicationEligibilityService().check(profile, vacancy)
            is_eligible = eligibility.eligible
            eligibility_message = eligibility.message

        sections = []
        for key, title, content in (
            ("description", "Job Description", vacancy.description),
            (
                "requirements",
                "Requirements",
                vacancy.requirements or vacancy.qualification_required,
            ),
            ("roles", "Roles & Responsibilities", vacancy.roles_responsibilities),
            (
                "teaching",
                "Teaching Responsibilities",
                vacancy.teaching_responsibilities,
            ),
            ("research", "Research Expectations", vacancy.research_expectations),
            (
                "benefits",
                "Benefits & Facilities",
                self._join_blocks(vacancy.benefits, vacancy.facilities),
            ),
        ):
            text = (content or "").strip()
            if text:
                sections.append(
                    VacancyDetailSection(key=key, title=title, content=text)
                )

        if college and getattr(college, "description", "").strip():
            sections.append(
                VacancyDetailSection(
                    key="about",
                    title=f"About {college.name}",
                    content=college.description.strip()
                )
            )

        posted = vacancy.published_at or vacancy.created_at
        deadline = None
        if vacancy.application_deadline:
            deadline = timezone.localtime(vacancy.application_deadline).strftime(
                "%b %d, %Y"
            )

        return ProfessorVacancyDetailContext(
            id=str(vacancy.pk),
            title=vacancy.title,
            institution_name=vacancy.college_name_snapshot
            or (college.name if college else ""),
            location=location,
            logo_url=logo,
            tags=tags,
            meta=meta,
            sections=sections,
            is_saved=saved_ids.get(str(vacancy.pk), False),
            has_applied=application is not None,
            application_status=application.get_status_display()
            if application
            else None,
            apply_url=pu("professor_apply_vacancy", vacancy_id=vacancy.pk),
            save_url=pu("professor_save_vacancy", vacancy_id=vacancy.pk),
            browse_url=pu("professor_browse_jobs") if user else "",
            posted_display=timezone.localtime(posted).strftime("%b %d, %Y")
            if posted
            else "—",
            deadline_display=deadline,
            application_detail_url=(
                pu("professor_application_detail", application_id=application.pk)
                if application
                else None
            ),
            institution_url=institution_profile_url(college),
            is_eligible=is_eligible,
            eligibility_message=eligibility_message,
        )

    @staticmethod
    def _location(vacancy: FacultyVacancy) -> str:
        parts = [vacancy.city, vacancy.state, vacancy.country]
        if vacancy.campus:
            parts.insert(0, vacancy.campus)
        return ", ".join(p for p in parts if p) or "Location not specified"

    @staticmethod
    def _tags(vacancy: FacultyVacancy) -> list[str]:
        tags = []
        if vacancy.department:
            tags.append(vacancy.department)
        if vacancy.designation:
            tags.append(vacancy.get_designation_display())
        if vacancy.employment_type:
            tags.append(vacancy.get_employment_type_display())
        if vacancy.work_type:
            tags.append(vacancy.get_work_type_display())
        salary = ProfessorVacancyPortalService._salary_display(vacancy)
        if salary:
            tags.append(salary)
        if vacancy.is_urgent:
            tags.append("Urgent")
        if vacancy.is_featured:
            tags.append("Featured")
        return tags

    @staticmethod
    def _salary_display(vacancy: FacultyVacancy) -> str | None:
        if vacancy.salary_visibility == SalaryVisibility.HIDDEN:
            return None
        if not vacancy.salary_min and not vacancy.salary_max:
            return None
        return format_salary_lpa(
            vacancy.salary_min,
            vacancy.salary_max,
            vacancy.salary_currency or "INR",
        )

    @staticmethod
    def _meta_rows(vacancy: FacultyVacancy) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        if vacancy.experience_min is not None or vacancy.experience_max is not None:
            if (
                vacancy.experience_min is not None
                and vacancy.experience_max is not None
            ):
                rows.append(
                    (
                        "Experience",
                        f"{vacancy.experience_min}–{vacancy.experience_max} years",
                    )
                )
            elif vacancy.experience_min is not None:
                rows.append(("Experience", f"{vacancy.experience_min}+ years"))
            else:
                rows.append(("Experience", f"Up to {vacancy.experience_max} years"))
        if vacancy.minimum_qualification:
            rows.append(
                ("Minimum Qualification", vacancy.get_minimum_qualification_display())
            )
        if vacancy.specialization_required:
            rows.append(("Specialization", vacancy.specialization_required))
        if vacancy.vacancy_count and vacancy.vacancy_count > 1:
            rows.append(("Openings", str(vacancy.vacancy_count)))
        if vacancy.joining_date:
            rows.append(("Expected Joining", vacancy.joining_date.strftime("%b %Y")))
        return rows

    @staticmethod
    def _join_blocks(*parts: str) -> str:
        return "\n\n".join(p.strip() for p in parts if p and p.strip())
