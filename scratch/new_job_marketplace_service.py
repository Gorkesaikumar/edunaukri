"""Enterprise job marketplace — search, filter, rank, and card mapping."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import Q, Value, CharField
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.applications.models import JobApplication
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_matching_service import JobMatchingService
from apps.it_recruitment.services.job_recommendation_engine_service import (
    JobRecommendationEngineService,
)
from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
    JobSeekerResumeAnalysisService,
)
from apps.faculty.constants.enums import (
    VacancyStatus,
    VacancyVisibility,
    WorkType as FacultyWorkType,
)
from apps.faculty.models import FacultyVacancy
from apps.jobs.constants.enums import EmploymentType, JobStatus, JobVisibility, WorkMode
from apps.jobs.models import JobPosting, SavedJob
from apps.jobs.services.saved_job_service import SavedJobService
from apps.reports.selectors.featured_jobs import FeaturedJobsSelector


def _to_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


@dataclass
class MarketplaceFilterParams:
    q: str = ""
    location: str = ""
    role: str = ""
    employment_type: str = ""
    work_mode: str = ""
    industry: str = ""
    company: str = ""
    company_id: str = ""
    education: str = ""
    skills: list[str] = field(default_factory=list)
    experience: int | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    posted_within: str = ""
    company_size: str = ""
    verified_only: bool = False
    remote_only: bool = False
    hybrid_only: bool = False
    onsite_only: bool = False
    featured_only: bool = False
    easy_apply: bool = False
    saved_only: bool = False
    sort: str = "recent"
    page: int = 1
    page_size: int = 12
    domain_filter: str = "all"


@dataclass
class MarketplaceJobCard:
    id: str
    title: str
    company_name: str
    company_id: str
    company_verified: bool
    logo_url: str | None
    logo_initial: str
    location: str
    salary_display: str | None
    experience_label: str | None
    employment_type_label: str
    work_mode_label: str
    skills: list[str]
    posted_display: str
    fresh_label: str
    is_fresh: bool
    is_featured: bool
    is_urgent: bool
    applicant_count: int
    deadline_display: str | None
    detail_url: str
    apply_url: str
    save_url: str | None
    share_url: str
    save_login_url: str | None = None
    match_percent: int | None = None
    is_saved: bool = False
    has_applied: bool = False
    can_apply: bool = True
    can_save: bool = False
    domain: str = "it"
    domain_label: str = "IT Domain"
    domain_icon: str = "bi-code-slash"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company_name": self.company_name,
            "company_id": self.company_id,
            "company_verified": self.company_verified,
            "logo_url": self.logo_url,
            "logo_initial": self.logo_initial,
            "location": self.location,
            "salary_display": self.salary_display,
            "experience_label": self.experience_label,
            "employment_type_label": self.employment_type_label,
            "work_mode_label": self.work_mode_label,
            "skills": self.skills,
            "posted_display": self.posted_display,
            "fresh_label": self.fresh_label,
            "is_fresh": self.is_fresh,
            "is_featured": self.is_featured,
            "is_urgent": self.is_urgent,
            "applicant_count": self.applicant_count,
            "deadline_display": self.deadline_display,
            "detail_url": self.detail_url,
            "apply_url": self.apply_url,
            "save_url": self.save_url,
            "save_login_url": self.save_login_url,
            "share_url": self.share_url,
            "match_percent": self.match_percent,
            "is_saved": self.is_saved,
            "has_applied": self.has_applied,
            "can_apply": self.can_apply,
            "can_save": self.can_save,
            "domain": self.domain,
            "domain_label": self.domain_label,
            "domain_icon": self.domain_icon,
        }


@dataclass
class MarketplacePageResult:
    jobs: list[MarketplaceJobCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    is_personalized: bool
    active_filters: list[dict]
    filter_options: dict

    def to_dict(self) -> dict:
        return {
            "jobs": [job.to_dict() for job in self.jobs],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "is_personalized": self.is_personalized,
            "active_filters": self.active_filters,
            "filter_options": self.filter_options,
        }


class JobMarketplaceService(BaseService):
    """Orchestrates marketplace discovery for guests and authenticated seekers."""

    POSTED_WINDOWS = {
        "hour": timedelta(hours=1),
        "today": None,
        "day": timedelta(days=1),
        "3days": timedelta(days=3),
        "week": timedelta(days=7),
    }

    GUEST_SORT_MAP = {
        "recent": lambda: ("-is_featured", "-published_at", "-created_at"),
        "featured": lambda: ("-is_featured", "-is_urgent", "-published_at"),
        "trending": lambda: ("-view_count", "-application_count", "-published_at"),
        "salary_high": lambda: ("-salary_max", "-published_at"),
        "salary_low": lambda: ("salary_min", "-published_at"),
        "title": lambda: ("title",),
        "match": lambda: ("-published_at",),
    }

    UNION_FIELDS = (
        "id",
        "domain",
        "published_at",
        "created_at",
        "is_featured",
        "is_urgent",
        "view_count",
        "application_count",
        "salary_max",
        "salary_min",
        "title",
    )

    def parse_filters(self, params) -> MarketplaceFilterParams:
        skills_raw = params.get("skills") or params.get("skill") or ""
        skills = (
            _split_csv(skills_raw)
            if isinstance(skills_raw, str)
            else list(skills_raw or [])
        )

        def as_int(name):
            raw = params.get(name)
            if raw in (None, ""):
                return None
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None

        def as_bool(name):
            raw = params.get(name)
            if raw is None:
                return False
            return str(raw).lower() in ("1", "true", "yes", "on")

        return MarketplaceFilterParams(
            q=(params.get("q") or params.get("query") or "").strip(),
            location=(params.get("location") or "").strip(),
            role=(params.get("role") or params.get("title") or "").strip(),
            employment_type=(params.get("employment_type") or "").strip(),
            work_mode=(params.get("work_mode") or "").strip(),
            industry=(params.get("industry") or "").strip(),
            company=(params.get("company") or "").strip(),
            company_id=(params.get("company_id") or "").strip(),
            education=(params.get("education") or "").strip(),
            skills=skills,
            experience=as_int("experience"),
            salary_min=_to_decimal(params.get("salary_min")),
            salary_max=_to_decimal(params.get("salary_max")),
            posted_within=(
                params.get("posted_within") or params.get("posted") or ""
            ).strip(),
            company_size=(params.get("company_size") or "").strip(),
            verified_only=as_bool("verified_only") or as_bool("verified"),
            remote_only=as_bool("remote_only") or as_bool("remote"),
            hybrid_only=as_bool("hybrid_only") or as_bool("hybrid"),
            onsite_only=as_bool("onsite_only") or as_bool("onsite"),
            featured_only=as_bool("featured_only") or as_bool("featured"),
            easy_apply=as_bool("easy_apply"),
            saved_only=as_bool("saved_only") or as_bool("saved"),
            sort=(params.get("sort") or "recent").strip(),
            page=max(1, as_int("page") or 1),
            page_size=min(48, max(6, as_int("page_size") or 12)),
            domain_filter=(params.get("domain") or "all").strip().lower(),
        )

    def browse(
        self,
        *,
        filters: MarketplaceFilterParams,
        user=None,
        profile: JobSeekerProfile | None = None,
    ) -> MarketplacePageResult:
        is_seeker = bool(
            user
            and user.is_authenticated
            and RoleAssignmentService().user_has_it_role(
                user, ITUserRoleType.JOB_SEEKER
            )
        )
        if is_seeker and profile is None:
            profile = (
                JobSeekerProfile.objects.filter(user=user, is_deleted=False)
                .select_related("resume_file")
                .prefetch_related("skills__skill")
                .first()
            )

        saved_ids: set = set()
        applied_ids: set = set()
        if profile:
            saved_ids = set(
                SavedJob.objects.filter(
                    job_seeker=profile, is_deleted=False
                ).values_list("job_posting_id", flat=True)
            )
            applied_ids = set(
                JobApplication.objects.filter(
                    job_seeker=profile, is_deleted=False
                ).values_list("job_posting_id", flat=True)
            )

        # Build Domain specific queries
        if filters.domain_filter == "faculty":
            it_qs = JobPosting.objects.none()
        else:
            it_qs = self._apply_it_filters(
                self._it_queryset(), filters, profile=profile, saved_ids=saved_ids
            )

        if filters.domain_filter == "it" or (filters.saved_only and is_seeker):
            fac_qs = FacultyVacancy.objects.none()
        else:
            fac_qs = self._apply_faculty_filters(self._faculty_queryset(), filters)

        it_vals = it_qs.annotate(domain=Value("it", CharField(max_length=10))).values(
            *self.UNION_FIELDS
        )
        fac_vals = fac_qs.annotate(
            domain=Value("faculty", CharField(max_length=10))
        ).values(*self.UNION_FIELDS)

        unified_qs = it_vals.union(fac_vals)

        # Handle IT Seeker personalization
        if is_seeker and profile and filters.sort in ("match", "recent", ""):
            jobs_with_domain, scores = self._rank_for_seeker(
                profile, unified_qs, applied_ids=applied_ids
            )
            is_personalized = True
        else:
            ordered_vals = list(self._order_for_guest(unified_qs, filters.sort))
            jobs_with_domain = self._hydrate_unified(ordered_vals)
            scores = {}
            is_personalized = False

        paginator = Paginator(jobs_with_domain, filters.page_size)
        page_obj = paginator.get_page(filters.page)
        page_items = list(page_obj.object_list)

        cards = [
            self._map_card(
                obj,
                domain=domain,
                user=user,
                profile=profile,
                match_percent=scores.get(obj.pk),
                is_saved=(domain == "it" and obj.pk in saved_ids),
                has_applied=(domain == "it" and obj.pk in applied_ids),
            )
            for obj, domain in page_items
        ]

        return MarketplacePageResult(
            jobs=cards,
            total_count=paginator.count,
            page=page_obj.number,
            page_size=filters.page_size,
            total_pages=paginator.num_pages,
            is_personalized=is_personalized,
            active_filters=self._active_filter_chips(filters),
            filter_options=self.filter_options(),
        )

    def get_job_detail(
        self,
        job_id,
        *,
        user=None,
        profile: JobSeekerProfile | None = None,
        domain: str = "it",
    ):
        is_seeker = bool(
            user
            and user.is_authenticated
            and RoleAssignmentService().user_has_it_role(
                user, ITUserRoleType.JOB_SEEKER
            )
        )
        if is_seeker and profile is None:
            profile = JobSeekerProfile.objects.filter(
                user=user, is_deleted=False
            ).first()

        match_percent = None
        is_saved = False
        has_applied = False
        skills_display = []
        related = []

        if domain == "it":
            job = (
                self._it_queryset()
                .filter(pk=job_id)
                .select_related(
                    "posted_by", "posted_by__user", "company", "company__logo_file"
                )
                .prefetch_related("required_skills__skill", "locations")
                .first()
            )
            if not job:
                return None

            skills_display = [
                rs.skill.name for rs in job.required_skills.all() if rs.skill_id
            ]
            related = self._related_it_jobs(job, profile=profile, exclude_id=job.pk)

            if profile:
                saved = SavedJob.objects.filter(
                    job_seeker=profile, job_posting=job, is_deleted=False
                ).exists()
                is_saved = saved
                has_applied = JobApplication.objects.filter(
                    job_seeker=profile, job_posting=job, is_deleted=False
                ).exists()
                engine = JobRecommendationEngineService()
                analysis = JobSeekerResumeAnalysisService().get_analysis(profile)
                behavioral = engine._behavioral_boosts(profile)
                match = JobMatchingService().score_job(
                    profile,
                    job,
                    analysis=analysis,
                    behavioral_boost=behavioral.get(job.pk, 0),
                )
                match_percent = match.score

        elif domain == "faculty":
            job = (
                self._faculty_queryset()
                .filter(pk=job_id)
                .select_related(
                    "posted_by", "posted_by__user", "college", "college__logo_file"
                )
                .first()
            )
            if not job:
                return None

            if job.specialization_required:
                skills_display = _split_csv(job.specialization_required)

            # Faculty matching logic could be implemented here for professors.

        card = self._map_card(
            job,
            domain=domain,
            user=user,
            profile=profile,
            match_percent=match_percent,
            is_saved=is_saved,
            has_applied=has_applied,
        )
        return {
            "job": job,
            "card": card,
            "skills": skills_display,
            "related_jobs": related,
            "is_authenticated": bool(user and user.is_authenticated),
            "is_job_seeker": is_seeker,
            "login_url": self._login_url(job, domain),
            "domain": domain,
        }

    def suggest(self, query: str, *, limit: int = 8) -> list[dict]:
        query = (query or "").strip()
        if len(query) < 2:
            return []

        it_qs = (
            self._it_queryset()
            .filter(
                Q(title__icontains=query)
                | Q(company_name_snapshot__icontains=query)
                | Q(city__icontains=query)
                | Q(required_skills__skill__name__icontains=query)
            )
            .distinct()
            .annotate(domain=Value("it", CharField(max_length=10)))
            .values(*self.UNION_FIELDS)
        )

        fac_qs = (
            self._faculty_queryset()
            .filter(
                Q(title__icontains=query)
                | Q(college_name_snapshot__icontains=query)
                | Q(city__icontains=query)
            )
            .distinct()
            .annotate(domain=Value("faculty", CharField(max_length=10)))
            .values(*self.UNION_FIELDS)
        )

        unified_qs = it_qs.union(fac_qs)[:limit]
        items_with_domain = self._hydrate_unified(unified_qs)

        results = []
        for obj, domain in items_with_domain:
            if domain == "it":
                sublabel = obj.company_name_snapshot
                url = reverse("marketplace_job_detail", kwargs={"job_id": obj.pk})
            else:
                sublabel = obj.college_name_snapshot
                url = reverse("marketplace_vacancy_detail", kwargs={"job_id": obj.pk})
            results.append(
                {
                    "type": "job",
                    "label": obj.title,
                    "sublabel": sublabel,
                    "url": url,
                }
            )
        return results

    def filter_options(self) -> dict:
        return {
            "employment_types": [
                {"value": c[0], "label": c[1]} for c in EmploymentType.choices
            ],
            "work_modes": [{"value": c[0], "label": c[1]} for c in WorkMode.choices],
            "posted_windows": [
                {"value": "hour", "label": "Last hour"},
                {"value": "today", "label": "Today"},
                {"value": "day", "label": "Last 24 hours"},
                {"value": "3days", "label": "Last 3 days"},
                {"value": "week", "label": "Last week"},
            ],
            "sort_options_guest": [
                {"value": "recent", "label": "Latest"},
                {"value": "featured", "label": "Featured"},
                {"value": "trending", "label": "Trending"},
                {"value": "salary_high", "label": "Salary: High to Low"},
                {"value": "salary_low", "label": "Salary: Low to High"},
            ],
            "sort_options_seeker": [
                {"value": "match", "label": "Best Match"},
                {"value": "recent", "label": "Recently Posted"},
                {"value": "featured", "label": "Featured"},
                {"value": "trending", "label": "Trending"},
                {"value": "salary_high", "label": "Salary: High to Low"},
            ],
        }

    def _it_queryset(self):
        now = timezone.now()
        return JobPosting.objects.filter(
            is_deleted=False,
            status=JobStatus.PUBLISHED,
            visibility=JobVisibility.PUBLIC,
            company__is_active=True,
            company__is_deleted=False,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

    def _faculty_queryset(self):
        now = timezone.now()
        return FacultyVacancy.objects.filter(
            is_deleted=False,
            status=VacancyStatus.PUBLISHED,
            visibility=VacancyVisibility.PUBLIC,
            college__is_deleted=False,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

    def _hydrate_unified(self, unified_vals_list) -> list[tuple]:
        it_ids = [item["id"] for item in unified_vals_list if item["domain"] == "it"]
        fac_ids = [
            item["id"] for item in unified_vals_list if item["domain"] == "faculty"
        ]

        it_jobs = JobPosting.objects.filter(id__in=it_ids).select_related(
            "company", "company__logo_file"
        )
        fac_vacs = FacultyVacancy.objects.filter(id__in=fac_ids).select_related(
            "college", "college__logo_file"
        )

        job_map = {str(j.id): (j, "it") for j in it_jobs}
        fac_map = {str(j.id): (j, "faculty") for j in fac_vacs}

        result = []
        for item in unified_vals_list:
            obj, domain = (
                job_map.get(str(item["id"]))
                or fac_map.get(str(item["id"]))
                or (None, None)
            )
            if obj:
                result.append((obj, domain))
        return result

    def _apply_it_filters(
        self, qs, filters: MarketplaceFilterParams, *, profile, saved_ids
    ):
        if filters.q:
            qs = qs.filter(
                Q(title__icontains=filters.q)
                | Q(description__icontains=filters.q)
                | Q(requirements__icontains=filters.q)
                | Q(job_code__icontains=filters.q)
                | Q(company_name_snapshot__icontains=filters.q)
                | Q(category__icontains=filters.q)
                | Q(department__icontains=filters.q)
                | Q(required_skills__skill__name__icontains=filters.q)
            ).distinct()
        if filters.role:
            qs = qs.filter(title__icontains=filters.role)
        if filters.location:
            qs = qs.filter(
                Q(location__icontains=filters.location)
                | Q(city__icontains=filters.location)
                | Q(state__icontains=filters.location)
                | Q(country__icontains=filters.location)
            )
        if filters.employment_type:
            qs = qs.filter(employment_type=filters.employment_type)
        if filters.work_mode:
            qs = qs.filter(work_mode=filters.work_mode)
        if filters.industry:
            qs = qs.filter(company__industry__icontains=filters.industry)
        if filters.company:
            qs = qs.filter(
                Q(company_name_snapshot__icontains=filters.company)
                | Q(company__name__icontains=filters.company)
            )
        if filters.company_id:
            qs = qs.filter(company_id=filters.company_id)
        if filters.education:
            qs = qs.filter(education_requirement__icontains=filters.education)
        if filters.skills:
            qs = qs.filter(
                required_skills__skill__name__in=filters.skills,
                required_skills__is_deleted=False,
            ).distinct()
        if filters.experience is not None:
            qs = qs.filter(
                Q(experience_min__lte=filters.experience)
                | Q(experience_min__isnull=True),
            ).filter(
                Q(experience_max__gte=filters.experience)
                | Q(experience_max__isnull=True),
            )
        if filters.salary_min is not None:
            qs = qs.filter(
                Q(salary_max__gte=filters.salary_min) | Q(salary_max__isnull=True)
            )
        if filters.salary_max is not None:
            qs = qs.filter(
                Q(salary_min__lte=filters.salary_max) | Q(salary_min__isnull=True)
            )
        if filters.company_size:
            qs = qs.filter(company__company_size=filters.company_size)
        if filters.verified_only:
            qs = qs
        if filters.remote_only:
            qs = qs.filter(Q(is_remote=True) | Q(work_mode=WorkMode.REMOTE))
        if filters.hybrid_only:
            qs = qs.filter(work_mode=WorkMode.HYBRID)
        if filters.onsite_only:
            qs = qs.filter(work_mode=WorkMode.ONSITE, is_remote=False)
        if filters.featured_only:
            qs = qs.filter(is_featured=True)
        if filters.easy_apply:
            qs = qs.filter(is_urgent=True)
        if filters.saved_only and profile:
            qs = qs.filter(pk__in=saved_ids or [])
        if filters.posted_within:
            qs = self._filter_posted_within(qs, filters.posted_within)
        return qs

    def _apply_faculty_filters(self, qs, filters: MarketplaceFilterParams):
        if filters.q:
            qs = qs.filter(
                Q(title__icontains=filters.q)
                | Q(description__icontains=filters.q)
                | Q(requirements__icontains=filters.q)
                | Q(vacancy_code__icontains=filters.q)
                | Q(college_name_snapshot__icontains=filters.q)
                | Q(designation__icontains=filters.q)
                | Q(department__icontains=filters.q)
            ).distinct()
        if filters.role:
            qs = qs.filter(title__icontains=filters.role)
        if filters.location:
            qs = qs.filter(
                Q(campus__icontains=filters.location)
                | Q(city__icontains=filters.location)
                | Q(state__icontains=filters.location)
                | Q(country__icontains=filters.location)
            )
        if filters.employment_type:
            qs = qs.filter(employment_type=filters.employment_type)
        if filters.work_mode:
            qs = qs.filter(work_type=filters.work_mode)
        if filters.industry:
            qs = qs.filter(college__institution_type__icontains=filters.industry)
        if filters.company:
            qs = qs.filter(
                Q(college_name_snapshot__icontains=filters.company)
                | Q(college__name__icontains=filters.company)
            )
        if filters.company_id:
            qs = qs.filter(college_id=filters.company_id)
        if filters.education:
            qs = qs.filter(minimum_qualification__icontains=filters.education)
        if filters.experience is not None:
            qs = qs.filter(
                Q(experience_min__lte=filters.experience)
                | Q(experience_min__isnull=True),
            ).filter(
                Q(experience_max__gte=filters.experience)
                | Q(experience_max__isnull=True),
            )
        if filters.salary_min is not None:
            qs = qs.filter(
                Q(salary_max__gte=filters.salary_min) | Q(salary_max__isnull=True)
            )
        if filters.salary_max is not None:
            qs = qs.filter(
                Q(salary_min__lte=filters.salary_max) | Q(salary_min__isnull=True)
            )
        if filters.company_size:
            # Faculty domain doesnt exactly map company size.
            pass
        if filters.verified_only:
            qs = qs
        if filters.remote_only:
            qs = qs.filter(work_type=FacultyWorkType.REMOTE)
        if filters.hybrid_only:
            qs = qs.filter(work_type=FacultyWorkType.HYBRID)
        if filters.onsite_only:
            qs = qs.filter(work_type=FacultyWorkType.ONSITE)
        if filters.featured_only:
            qs = qs.filter(is_featured=True)
        if filters.easy_apply:
            qs = qs.filter(is_urgent=True)
        if filters.posted_within:
            qs = self._filter_posted_within(qs, filters.posted_within)
        return qs

    def _filter_posted_within(self, qs, window: str):
        now = timezone.now()
        if window == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return qs.filter(published_at__gte=start)
        delta = self.POSTED_WINDOWS.get(window)
        if delta:
            return qs.filter(published_at__gte=now - delta)
        return qs

    def _order_for_guest(self, qs, sort: str):
        order = self.GUEST_SORT_MAP.get(sort, self.GUEST_SORT_MAP["recent"])()
        return qs.order_by(*order)

    def _rank_for_seeker(self, profile: JobSeekerProfile, qs, *, applied_ids: set):
        cap = 400
        vals = list(qs[:cap])
        if not vals:
            return [], {}

        items_with_domain = self._hydrate_unified(vals)

        engine = JobRecommendationEngineService()
        analysis = JobSeekerResumeAnalysisService().get_analysis(profile)
        behavioral = engine._behavioral_boosts(profile)
        matcher = JobMatchingService()

        scored: list[tuple[tuple, int]] = []
        applied_jobs = []

        for item_tuple in items_with_domain:
            obj, domain = item_tuple
            if obj.pk in applied_ids and domain == "it":
                applied_jobs.append(item_tuple)
                continue

            boost = 0
            score = 0

            if domain == "it":
                result = matcher.score_job(
                    profile,
                    obj,
                    analysis=analysis,
                    behavioral_boost=behavioral.get(obj.pk, 0),
                )
                score = result.score
                if obj.company:
                    boost += 2
            else:
                score = 0

            if obj.is_featured:
                boost += 3

            scored.append((item_tuple, score + boost))

        scored.sort(
            key=lambda item: (
                item[1],
                item[0][0].is_featured,
                item[0][0].published_at or item[0][0].created_at,
            ),
            reverse=True,
        )

        ranked_jobs = [item for item, _ in scored] + applied_jobs
        scores = {item[0].pk: score for item, score in scored}
        return ranked_jobs, scores

    def _related_it_jobs(self, job: JobPosting, *, profile, exclude_id, limit=4):
        qs = (
            self._it_queryset()
            .filter(Q(company=job.company) | Q(category=job.category))
            .exclude(pk=exclude_id)
            .order_by("-is_featured", "-published_at")[: limit * 2]
        )
        if profile:
            # We can use the old _rank_for_seeker logic just for these IT jobs
            engine = JobRecommendationEngineService()
            analysis = JobSeekerResumeAnalysisService().get_analysis(profile)
            behavioral = engine._behavioral_boosts(profile)
            matcher = JobMatchingService()

            jobs = list(qs[:limit])
            for j in jobs:
                match = matcher.score_job(
                    profile,
                    j,
                    analysis=analysis,
                    behavioral_boost=behavioral.get(j.pk, 0),
                )
                j._score = match.score

            jobs.sort(key=lambda j: j._score, reverse=True)
            return [
                self._map_card(j, domain="it", profile=profile, match_percent=j._score)
                for j in jobs
            ]
        return [self._map_card(j, domain="it") for j in qs[:limit]]

    def _map_card(
        self,
        job,
        *,
        domain="it",
        user=None,
        profile=None,
        match_percent=None,
        is_saved=False,
        has_applied=False,
    ) -> MarketplaceJobCard:
        mapper = FeaturedJobsSelector()

        if domain == "it":
            company = job.company
            org_name = job.company_name_snapshot or (company.name if company else "")
            location = mapper._location(
                city=job.city,
                state=job.state,
                remote=job.is_remote,
                fallback=job.location,
            )
            logo_url = mapper._logo_url(company.logo_file if company else None)
            emp_type = job.get_employment_type_display()
            work_mode = job.get_work_mode_display()
            skills = (
                [
                    rs.skill.name
                    for rs in job.required_skills.all()
                    if rs.skill_id and not rs.is_deleted
                ][:6]
                if hasattr(job, "required_skills")
                else []
            )
            company_id = str(job.company_id)
            domain_label = "IT Domain"
            domain_icon = "bi-code-slash"
            detail_url = reverse("marketplace_job_detail", kwargs={"job_id": job.pk})
        else:
            college = job.college
            org_name = job.college_name_snapshot or (college.name if college else "")
            location = mapper._location(
                city=job.city, state=job.state, remote=False, fallback=job.campus
            )
            logo_url = mapper._logo_url(college.logo_file if college else None)
            emp_type = job.get_employment_type_display()
            work_mode = job.get_work_type_display()
            skills = (
                _split_csv(job.specialization_required)[:6]
                if hasattr(job, "specialization_required")
                else []
            )
            company_id = str(job.college_id)
            domain_label = "Faculty Domain"
            domain_icon = "bi-mortarboard"
            detail_url = reverse(
                "marketplace_vacancy_detail", kwargs={"job_id": job.pk}
            )

        published = job.published_at or job.created_at
        posted_display = mapper._posted(published)
        fresh_label, is_fresh = self._freshness(published)

        is_seeker = bool(
            user
            and user.is_authenticated
            and profile
            and RoleAssignmentService().user_has_it_role(
                user, ITUserRoleType.JOB_SEEKER
            )
        )

        login_next = quote(detail_url, safe="")

        if domain == "it":
            apply_url = (
                reverse("marketplace_job_apply", kwargs={"job_id": job.pk})
                if is_seeker
                else f"{reverse('it_login_job_seeker')}?next={login_next}"
            )
            save_url = (
                reverse("marketplace_job_save", kwargs={"job_id": job.pk})
                if is_seeker
                else None
            )
            save_login = (
                SavedJobService.login_url_with_save(detail_url, job.pk)
                if not is_seeker
                else None
            )
            can_save = is_seeker
        else:
            apply_url = (
                detail_url  # Faculty jobs redirect to their detail page for applying
            )
            save_url = None
            save_login = None
            can_save = False

        deadline_display = None
        if job.application_deadline:
            deadline_display = timezone.localtime(job.application_deadline).strftime(
                "%b %d, %Y"
            )

        return MarketplaceJobCard(
            id=str(job.pk),
            title=job.title,
            company_name=org_name,
            company_id=company_id,
            company_verified=True,
            logo_url=logo_url,
            logo_initial=(org_name[:1] or "E").upper(),
            location=location,
            salary_display=mapper._salary(
                job.salary_min, job.salary_max, job.salary_visibility
            ),
            experience_label=mapper._experience(job.experience_min),
            employment_type_label=emp_type,
            work_mode_label=work_mode,
            skills=skills,
            posted_display=posted_display,
            fresh_label=fresh_label,
            is_fresh=is_fresh,
            is_featured=job.is_featured,
            is_urgent=job.is_urgent,
            applicant_count=job.application_count,
            deadline_display=deadline_display,
            detail_url=detail_url,
            apply_url=apply_url,
            save_url=save_url,
            save_login_url=save_login,
            share_url=detail_url,
            match_percent=match_percent if is_seeker else None,
            is_saved=is_saved,
            has_applied=has_applied,
            can_apply=not has_applied,
            can_save=can_save,
            domain=domain,
            domain_label=domain_label,
            domain_icon=domain_icon,
        )

    @staticmethod
    def _freshness(published_at):
        if not published_at:
            return "", False
        delta = timezone.now() - published_at
        if delta <= timedelta(hours=1):
            return "New · Last hour", True
        if delta <= timedelta(days=1):
            hours = max(1, delta.seconds // 3600)
            return f"New · {hours}h ago", True
        if delta <= timedelta(days=3):
            return f"New · {delta.days}d ago", True
        if delta <= timedelta(days=7):
            return f"Fresh · {delta.days}d ago", True
        return "", False

    @staticmethod
    def _login_url(job, domain="it") -> str:
        if domain == "it":
            next_url = quote(
                reverse("marketplace_job_detail", kwargs={"job_id": job.pk}), safe=""
            )
            return f"{reverse('it_login_job_seeker')}?next={next_url}"
        else:
            next_url = quote(
                reverse("marketplace_vacancy_detail", kwargs={"job_id": job.pk}),
                safe="",
            )
            return f"{reverse('faculty_login_professor')}?next={next_url}"

    @staticmethod
    def _active_filter_chips(filters: MarketplaceFilterParams) -> list[dict]:
        chips = []
        mapping = [
            ("q", filters.q, "Search"),
            ("location", filters.location, "Location"),
            ("role", filters.role, "Role"),
            ("employment_type", filters.employment_type, "Type"),
            ("work_mode", filters.work_mode, "Work mode"),
            ("industry", filters.industry, "Industry"),
            ("company", filters.company, "Company"),
            ("education", filters.education, "Education"),
            (
                "domain_filter",
                filters.domain_filter if filters.domain_filter != "all" else "",
                "Domain",
            ),
        ]
        for key, value, label in mapping:
            if value:
                chips.append({"key": key, "label": label, "value": value})
        if filters.skills:
            chips.append(
                {"key": "skills", "label": "Skills", "value": ", ".join(filters.skills)}
            )
        if filters.verified_only:
            chips.append({"key": "verified_only", "label": "Verified", "value": "Yes"})
        if filters.remote_only:
            chips.append({"key": "remote_only", "label": "Remote", "value": "Yes"})
        if filters.featured_only:
            chips.append({"key": "featured_only", "label": "Featured", "value": "Yes"})
        if filters.saved_only:
            chips.append({"key": "saved_only", "label": "Saved", "value": "Yes"})
        return chips
