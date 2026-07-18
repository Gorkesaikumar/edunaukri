"""IT candidate marketplace for recruiter talent search."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.profiles.constants.enums import ProfileStatus
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_expected_salary_lpa,
    initials_from_name,
    media_url,
)
from apps.it_recruitment.services.jobseeker_privacy_service import (
    JobSeekerPrivacyService,
)


@dataclass
class RecruiterCandidateMarketplaceContext:
    candidates: list[dict]
    filters: dict
    filter_options: dict
    stats: dict
    urls: dict


class RecruiterCandidateMarketplaceService(BaseService):
    """Search and filter IT job seekers visible to recruiters."""

    def build(
        self, profile: RecruiterProfile, *, params: dict | None = None
    ) -> RecruiterCandidateMarketplaceContext:
        params = params or {}
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        privacy = JobSeekerPrivacyService()

        qs = (
            JobSeekerProfile.objects.filter(
                is_deleted=False, profile_status=ProfileStatus.ACTIVE
            )
            .select_related("user", "profile_photo", "resume_file")
            .prefetch_related("skills__skill")
        )
        qs = privacy.filter_searchable_queryset(qs, user)
        qs = self._apply_filters(qs, params)
        total = qs.count()
        rows = qs[:60]

        candidates = [
            self._serialize_seeker(seeker, profile, pu, privacy) for seeker in rows
        ]

        return RecruiterCandidateMarketplaceContext(
            candidates=candidates,
            filters=self._filter_state(params),
            filter_options=self._filter_options(),
            stats={"total": total, "shown": len(candidates)},
            urls={
                "marketplace": pu("recruiter_candidate_marketplace"),
                "messages": pu("recruiter_messages"),
                "applicants": pu("recruiter_candidates"),
                "saved": pu("recruiter_saved_candidates"),
                "detail_template": pu(
                    "recruiter_candidate_marketplace_detail",
                    seeker_id="00000000-0000-0000-0000-000000000000",
                ),
            },
        )

    def get_seeker_detail(self, profile: RecruiterProfile, seeker_id) -> dict | None:
        privacy = JobSeekerPrivacyService()
        seeker = (
            JobSeekerProfile.objects.filter(pk=seeker_id, is_deleted=False)
            .select_related("user", "profile_photo", "resume_file")
            .prefetch_related("skills__skill", "experiences", "education")
            .first()
        )
        if not seeker or not privacy.can_view_profile(seeker, profile.user):
            return None
        pu = lambda name, **kw: PortalURLService.recruiter(profile.user, name, **kw)
        data = self._serialize_seeker(seeker, profile, pu, privacy, detailed=True)
        data["experiences"] = [
            {
                "title": exp.title,
                "company": exp.company_name,
                "duration": exp.location or "—",
            }
            for exp in seeker.experiences.filter(is_deleted=False).order_by(
                "-start_date"
            )[:5]
        ]
        data["education"] = [
            {
                "degree": edu.degree or edu.get_education_level_display(),
                "institution": edu.institution,
            }
            for edu in seeker.education.filter(is_deleted=False).order_by("-end_year")[
                :3
            ]
        ]
        data["summary"] = seeker.summary or seeker.headline or ""
        return data

    def _apply_filters(self, qs, params):
        q = (params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(headline__icontains=q)
                | Q(current_location__icontains=q)
                | Q(preferred_location__icontains=q)
                | Q(skills__skill__name__icontains=q)
                | Q(experiences__title__icontains=q)
                | Q(experiences__company_name__icontains=q)
            ).distinct()

        skills = (params.get("skills") or "").strip()
        if skills:
            for token in [s.strip() for s in skills.split(",") if s.strip()]:
                qs = qs.filter(skills__skill__name__icontains=token)
            qs = qs.distinct()

        if params.get("experience_min"):
            try:
                qs = qs.filter(experience_years__gte=int(params["experience_min"]))
            except (TypeError, ValueError):
                pass
        if params.get("experience_max"):
            try:
                qs = qs.filter(experience_years__lte=int(params["experience_max"]))
            except (TypeError, ValueError):
                pass

        location = (params.get("location") or "").strip()
        if location:
            qs = qs.filter(
                Q(current_location__icontains=location)
                | Q(preferred_location__icontains=location)
            )

        if params.get("work_mode"):
            qs = qs.filter(work_mode_preference=params["work_mode"])

        if params.get("employment_type"):
            qs = qs.filter(employment_type_preference=params["employment_type"])

        if params.get("notice_period"):
            try:
                qs = qs.filter(notice_period_days__lte=int(params["notice_period"]))
            except (TypeError, ValueError):
                pass

        education = (params.get("education") or "").strip()
        if education:
            qs = qs.filter(
                Q(education__degree__icontains=education)
                | Q(education__institution__icontains=education)
            ).distinct()

        if params.get("salary_min"):
            try:
                lpa = float(params["salary_min"])
                qs = qs.filter(expected_salary__gte=lpa * 100000)
            except (TypeError, ValueError):
                pass
        if params.get("salary_max"):
            try:
                lpa = float(params["salary_max"])
                qs = qs.filter(expected_salary__lte=lpa * 100000)
            except (TypeError, ValueError):
                pass

        if params.get("availability") == "immediate":
            qs = qs.filter(notice_period_days__lte=15)
        elif params.get("availability") == "30d":
            qs = qs.filter(notice_period_days__lte=30)

        if params.get("completion_min"):
            try:
                qs = qs.filter(profile_completeness__gte=int(params["completion_min"]))
            except (TypeError, ValueError):
                pass

        if params.get("has_resume") == "1":
            qs = qs.filter(resume_file__isnull=False)

        if params.get("recently_active") == "1":
            cutoff = timezone.now() - timedelta(days=30)
            qs = qs.filter(updated_at__gte=cutoff)

        sort = (params.get("sort") or "recent").strip()
        if sort == "experience":
            return qs.order_by("-experience_years", "-updated_at")
        if sort == "completion":
            return qs.order_by("-profile_completeness", "-updated_at")
        return qs.order_by("-updated_at")

    def _serialize_seeker(
        self, seeker, recruiter, pu, privacy, *, detailed: bool = False
    ) -> dict:
        skill_names = [
            link.skill.name
            for link in seeker.skills.filter(is_deleted=False).select_related("skill")[
                :8
            ]
            if getattr(link, "skill", None)
        ]
        can_resume = privacy.can_download_resume(seeker, recruiter.user)
        return {
            "id": str(seeker.pk),
            "name": seeker.full_name,
            "initials": initials_from_name(seeker.full_name, "JS"),
            "photo_url": media_url(seeker.profile_photo),
            "headline": seeker.headline or "IT Professional",
            "location": seeker.current_location or seeker.preferred_location or "—",
            "experience_years": seeker.experience_years
            if seeker.experience_years is not None
            else "—",
            "expected_salary": format_expected_salary_lpa(seeker.expected_salary)
            if seeker.expected_salary
            else "—",
            "work_mode": seeker.get_work_mode_preference_display()
            if seeker.work_mode_preference
            else "—",
            "notice_period": f"{seeker.notice_period_days} days"
            if seeker.notice_period_days
            else "—",
            "employment_type": seeker.get_employment_type_preference_display()
            if seeker.employment_type_preference
            else "—",
            "profile_completion": seeker.profile_completeness,
            "has_resume": bool(seeker.resume_file_id),
            "can_download_resume": can_resume,
            "skills": skill_names,
            "updated_label": timezone.localtime(seeker.updated_at).strftime("%b %d, %Y")
            if seeker.updated_at
            else "—",
            "detail_url": pu(
                "recruiter_candidate_marketplace_detail", seeker_id=seeker.pk
            ),
            "resume_url": pu("recruiter_marketplace_resume_api", seeker_id=seeker.pk)
            if can_resume
            else "",
            "messages_url": pu("recruiter_messages"),
            "interviews_url": pu("recruiter_interviews"),
            "saved_url": pu("recruiter_saved_candidates"),
            "applicants_url": pu("recruiter_candidates"),
        }

    @staticmethod
    def _filter_state(params: dict) -> dict:
        keys = (
            "q",
            "skills",
            "experience_min",
            "experience_max",
            "education",
            "location",
            "salary_min",
            "salary_max",
            "work_mode",
            "employment_type",
            "notice_period",
            "completion_min",
            "has_resume",
            "recently_active",
            "availability",
            "sort",
        )
        return {key: params.get(key, "") for key in keys}

    @staticmethod
    def _filter_options() -> dict:
        from apps.accounts.profiles.constants.enums import (
            EmploymentTypePreference,
            WorkModePreference,
        )

        return {
            "work_modes": WorkModePreference.choices,
            "employment_types": EmploymentTypePreference.choices,
            "sort_options": [
                ("recent", "Recently updated"),
                ("experience", "Most experience"),
                ("completion", "Profile completion"),
            ],
            "availability_options": [
                ("", "Any availability"),
                ("immediate", "Immediate (≤15 days notice)"),
                ("30d", "Within 30 days"),
            ],
        }
