"""Recruiter job creation page — form context and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.constants.enums import (
    EmploymentType,
    JobStatus,
    SalaryVisibility,
    WorkMode,
)


@dataclass
class RecruiterJobCreatePortalContext:
    has_company: bool
    can_publish: bool
    companies: list[dict]
    employment_types: list[tuple]
    work_modes: list[tuple]
    salary_visibilities: list[tuple]
    job_statuses: list[tuple]
    urls: dict


class RecruiterJobCreatePortalService(BaseService):
    def build(self, profile: RecruiterProfile) -> RecruiterJobCreatePortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        memberships = (
            CompanyMemberSelector().for_recruiter(profile).select_related("company")
        )
        companies = [
            {
                "id": str(m.company_id),
                "name": m.company.name,
                "can_publish_jobs": m.company.can_publish_jobs,
            }
            for m in memberships
        ]
        return RecruiterJobCreatePortalContext(
            has_company=bool(companies),
            can_publish=any(c["can_publish_jobs"] for c in companies),
            companies=companies,
            employment_types=EmploymentType.choices,
            work_modes=WorkMode.choices,
            salary_visibilities=SalaryVisibility.choices,
            job_statuses=JobStatus.choices,
            urls={
                "manage_jobs": pu("recruiter_jobs"),
                "profile": pu("recruiter_profile"),
            },
        )

    @staticmethod
    def parse_form(post) -> dict:
        title = (post.get("title") or "").strip()
        description = (post.get("description") or "").strip()
        requirements = (post.get("requirements") or "").strip()
        location = (post.get("location") or "").strip()
        employment_type = (
            post.get("employment_type") or EmploymentType.FULL_TIME
        ).strip()
        work_mode = (post.get("work_mode") or WorkMode.ONSITE).strip()
        errors: list[str] = []
        if not title:
            errors.append("Job title is required.")
        if not description:
            errors.append("Job description is required.")
        if len(title) > 200:
            errors.append("Job title must be 200 characters or fewer.")
        experience_min = post.get("experience_min") or None
        experience_max = post.get("experience_max") or None
        salary_min = post.get("salary_min") or None
        salary_max = post.get("salary_max") or None

        def _parse_num(value, is_float=False, is_lpa=False):
            if value is None or str(value).strip() == "":
                return None
            try:
                val = float(value) if is_float or is_lpa else int(value)
                if is_lpa:
                    if val < 1000:
                        return val * 100000
                    return val
                return val
            except (ValueError, TypeError):
                return None

        def _parse_skills(key):
            if hasattr(post, "getlist") and post.getlist(key):
                vals = post.getlist(key)
                if len(vals) == 1 and "," in str(vals[0]):
                    return [s.strip() for s in str(vals[0]).split(",") if s.strip()]
                return [str(s).strip() for s in vals if str(s).strip()]
            raw = post.get(key) or ""
            if isinstance(raw, (list, tuple)):
                return [str(s).strip() for s in raw if str(s).strip()]
            return [s.strip() for s in str(raw).split(",") if s.strip()]

        return {
            "errors": errors,
            "data": {
                "title": title,
                "description": description,
                "requirements": requirements,
                "location": location,
                "is_remote": work_mode == "remote"
                or post.get("is_remote") in ("on", "true", True, "1", 1),
                "employment_type": employment_type,
                "experience_min": _parse_num(experience_min),
                "experience_max": _parse_num(experience_max),
                "salary_min": _parse_num(salary_min, is_lpa=True),
                "salary_max": _parse_num(salary_max, is_lpa=True),
                "work_mode": work_mode,
                "salary_currency": (post.get("salary_currency") or "INR").strip(),
                "salary_visibility": (
                    post.get("salary_visibility") or SalaryVisibility.VISIBLE
                ).strip(),
                "vacancies": _parse_num(post.get("vacancies")) or 1,
                "job_code": (post.get("job_code") or "").strip(),
                "category": (post.get("category") or "").strip(),
                "department": (post.get("department") or "").strip(),
                "roles_responsibilities": (
                    post.get("roles_responsibilities") or ""
                ).strip(),
                "benefits": (post.get("benefits") or "").strip(),
                "education_requirement": (
                    post.get("education_requirement") or ""
                ).strip(),
                "joining_timeline": (post.get("joining_timeline") or "").strip(),
                "application_deadline": post.get("application_deadline") or None,
                "country": (post.get("country") or "").strip(),
                "state": (post.get("state") or "").strip(),
                "city": (post.get("city") or "").strip() or location,
                "office_address": (post.get("office_address") or "").strip(),
                "required_skills": _parse_skills("required_skills"),
                "preferred_skills": _parse_skills("preferred_skills"),
            },
            "form": {
                "title": title,
                "description": description,
                "requirements": requirements,
                "location": location,
                "is_remote": work_mode == "remote"
                or post.get("is_remote") in ("on", "true", True, "1", 1),
                "employment_type": employment_type,
                "experience_min": experience_min or "",
                "experience_max": experience_max or "",
                "salary_min": salary_min or "",
                "salary_max": salary_max or "",
                "work_mode": work_mode,
                "salary_currency": post.get("salary_currency") or "INR",
                "salary_visibility": post.get("salary_visibility")
                or SalaryVisibility.VISIBLE,
                "vacancies": post.get("vacancies") or "",
                "job_code": post.get("job_code") or "",
                "category": post.get("category") or "",
                "department": post.get("department") or "",
                "roles_responsibilities": post.get("roles_responsibilities") or "",
                "benefits": post.get("benefits") or "",
                "education_requirement": post.get("education_requirement") or "",
                "joining_timeline": post.get("joining_timeline") or "",
                "application_deadline": post.get("application_deadline") or "",
                "country": post.get("country") or "",
                "state": post.get("state") or "",
                "city": post.get("city") or "",
                "office_address": post.get("office_address") or "",
                "required_skills": ", ".join(_parse_skills("required_skills")),
                "preferred_skills": ", ".join(_parse_skills("preferred_skills")),
            },
        }
