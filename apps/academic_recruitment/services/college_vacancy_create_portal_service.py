"""Institution vacancy create/edit form helpers."""

from __future__ import annotations

from dataclasses import dataclass

from apps.authentication.services.portal_url_service import PortalURLService
from apps.colleges.selectors.college_selector import (
    CollegeMemberSelector,
    CollegeSelector,
)
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import EmploymentType, SalaryVisibility, WorkType
from apps.accounts.models.college_user import CollegeUser


@dataclass
class CollegeVacancyCreatePortalContext:
    has_institution: bool
    can_publish: bool
    institution: dict | None
    employment_types: list[tuple]
    work_types: list[tuple]
    salary_visibilities: list[tuple]
    urls: dict


class CollegeVacancyCreatePortalService(BaseService):
    def build(self, user: CollegeUser) -> CollegeVacancyCreatePortalContext:
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        from apps.academic_recruitment.services.college_portal_helpers import (
            primary_institution_for_user,
        )

        institution = primary_institution_for_user(user)
        has_institution = CollegeMemberSelector().has_active_membership(user)
        return CollegeVacancyCreatePortalContext(
            has_institution=has_institution,
            can_publish=bool(institution and institution.get("can_publish")),
            institution=institution,
            employment_types=EmploymentType.choices,
            work_types=WorkType.choices,
            salary_visibilities=SalaryVisibility.choices,
            urls={
                "manage_vacancies": pu("college_vacancies"),
                "profile": pu("college_profile"),
            },
        )

    @staticmethod
    def primary_college_id(user: CollegeUser):
        membership = CollegeMemberSelector().primary_for_user(user)
        if membership:
            return membership.college_id
        college = CollegeSelector().for_college_user(user).first()
        return college.pk if college else None

    @staticmethod
    def _get_college_obj(user: CollegeUser):
        membership = CollegeMemberSelector().primary_for_user(user)
        if membership:
            return membership.college
        return CollegeSelector().for_college_user(user).first()

    @staticmethod
    def parse_form(post) -> dict:
        title = (post.get("title") or "").strip()
        description = (post.get("description") or "").strip()
        department = (post.get("department") or "").strip()
        errors: list[str] = []
        if not title:
            errors.append("Vacancy title is required.")
        if not description:
            errors.append("Description is required.")
        if len(title) > 300:
            errors.append("Title must be 300 characters or fewer.")

        def _parse_num(value, is_lpa=False):
            if value is None or str(value).strip() == "":
                return None
            try:
                val = float(value) if is_lpa else int(value)
                if is_lpa and val < 1000:
                    return val * 100000
                return val
            except (ValueError, TypeError):
                return None

        work_type = (post.get("work_type") or WorkType.ONSITE).strip()
        data = {
            "title": title,
            "description": description,
            "department": department,
            "employment_type": (
                post.get("employment_type") or EmploymentType.FULL_TIME
            ).strip(),
            "work_type": work_type,
            "experience_min": _parse_num(post.get("experience_min")),
            "experience_max": _parse_num(post.get("experience_max")),
            "salary_min": _parse_num(post.get("salary_min"), is_lpa=True),
            "salary_max": _parse_num(post.get("salary_max"), is_lpa=True),
            "salary_currency": (post.get("salary_currency") or "INR").strip(),
            "salary_visibility": (
                post.get("salary_visibility") or SalaryVisibility.VISIBLE
            ).strip(),
            "vacancy_count": _parse_num(post.get("vacancy_count")) or 1,
            "city": (post.get("city") or "").strip(),
            "state": (post.get("state") or "").strip(),
            "country": (post.get("country") or "India").strip(),
        }
        designation = (post.get("designation") or "").strip()
        if designation:
            data["designation"] = designation
        requirements = (post.get("requirements") or "").strip()
        if requirements:
            data["requirements"] = requirements
        for optional in (
            "roles_responsibilities",
            "teaching_responsibilities",
            "research_expectations",
            "minimum_qualification",
            "specialization_required",
        ):
            value = (post.get(optional) or "").strip()
            if value:
                data[optional] = value

        return {
            "errors": errors,
            "data": data,
            "form": {k: post.get(k, "") for k in post},
        }
