"""Unified Institutions Marketplace — IT companies and faculty colleges."""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote

from django.core.paginator import Paginator
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants.enums import ITUserRoleType
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.colleges.models import College
from apps.companies.models import Company, CompanyMember
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import VacancyStatus, VacancyVisibility
from apps.faculty.models import FacultyVacancy
from apps.jobs.constants.enums import JobStatus, JobVisibility
from apps.jobs.models import JobPosting
from apps.reports.selectors.featured_jobs import FeaturedJobsSelector
from apps.reports.selectors.hiring_partners import HiringPartnersSelector


@dataclass
class InstitutionFilterParams:
    q: str = ""
    domain: str = ""
    location: str = ""
    industry: str = ""
    company_size: str = ""
    hiring_only: bool = False
    verified_only: bool = True
    sort: str = "openings"
    page: int = 1
    page_size: int = 12


@dataclass
class InstitutionCard:
    slug: str
    name: str
    domain: str
    domain_label: str
    domain_icon: str
    verified: bool
    description: str
    location: str
    headquarters: str
    type_label: str
    established_year: int | None
    employee_label: str
    open_positions: int
    open_positions_label: str
    is_hiring: bool
    hiring_label: str
    hiring_status: str
    logo_url: str | None
    banner_url: str | None
    logo_initial: str
    profile_url: str
    rating_ready: bool = True

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "domain": self.domain,
            "domain_label": self.domain_label,
            "domain_icon": self.domain_icon,
            "verified": self.verified,
            "description": self.description,
            "location": self.location,
            "headquarters": self.headquarters,
            "type_label": self.type_label,
            "established_year": self.established_year,
            "employee_label": self.employee_label,
            "open_positions": self.open_positions,
            "open_positions_label": self.open_positions_label,
            "is_hiring": self.is_hiring,
            "hiring_label": self.hiring_label,
            "hiring_status": self.hiring_status,
            "logo_url": self.logo_url,
            "banner_url": self.banner_url,
            "logo_initial": self.logo_initial,
            "profile_url": self.profile_url,
        }


@dataclass
class InstitutionOpening:
    id: str
    title: str
    domain: str
    location: str
    salary_display: str | None
    experience_label: str | None
    work_mode_label: str
    employment_type_label: str
    posted_display: str
    detail_url: str
    apply_url: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "domain": self.domain,
            "location": self.location,
            "salary_display": self.salary_display,
            "experience_label": self.experience_label,
            "work_mode_label": self.work_mode_label,
            "employment_type_label": self.employment_type_label,
            "posted_display": self.posted_display,
            "detail_url": self.detail_url,
            "apply_url": self.apply_url,
        }


@dataclass
class InstitutionProfile:
    slug: str
    name: str
    domain: str
    domain_label: str
    domain_icon: str
    verified: bool
    description: str
    mission: str
    vision: str
    culture: str
    industry: str
    type_label: str
    founded_year: int | None
    headquarters: str
    address: str
    website_url: str
    email: str
    phone: str
    company_size_label: str
    employee_label: str
    open_positions: int
    recruiter_count: int
    total_applicants: int
    logo_url: str | None
    banner_url: str | None
    logo_initial: str
    benefits: list[str] = field(default_factory=list)
    gallery: list[dict] = field(default_factory=list)
    openings: list[InstitutionOpening] = field(default_factory=list)
    is_hiring: bool = False
    hiring_label: str = ""
    share_url: str = ""


@dataclass
class InstitutionBrowseResult:
    institutions: list[InstitutionCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filter_options: dict
    active_filters: list[dict]

    def to_dict(self) -> dict:
        return {
            "institutions": [item.to_dict() for item in self.institutions],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "filter_options": self.filter_options,
            "active_filters": self.active_filters,
        }


class InstitutionMarketplaceService(BaseService):
    """Browse and profile pages for IT companies and faculty institutions."""

    def __init__(self):
        self._partners = HiringPartnersSelector()
        self._mapper = FeaturedJobsSelector()

    def parse_filters(self, params) -> InstitutionFilterParams:
        def as_bool(name, default=False):
            raw = params.get(name)
            if raw is None:
                return default
            return str(raw).lower() in ("1", "true", "yes", "on")

        def as_int(name, default):
            try:
                return int(params.get(name) or default)
            except (TypeError, ValueError):
                return default

        return InstitutionFilterParams(
            q=(params.get("q") or "").strip(),
            domain=(params.get("domain") or params.get("type") or "").strip().lower(),
            location=(params.get("location") or "").strip(),
            industry=(params.get("industry") or "").strip(),
            company_size=(params.get("company_size") or "").strip(),
            hiring_only=as_bool("hiring_only") or as_bool("hiring"),
            verified_only=as_bool("verified_only", True),
            sort=(params.get("sort") or "openings").strip(),
            page=max(1, as_int("page", 1)),
            page_size=min(48, max(6, as_int("page_size", 12))),
        )

    def browse(self, *, filters: InstitutionFilterParams) -> InstitutionBrowseResult:
        cards: list[InstitutionCard] = []
        if filters.domain in ("", "all", "it", "company"):
            cards.extend(self._company_cards(filters))
        if filters.domain in ("", "all", "faculty", "college"):
            cards.extend(self._college_cards(filters))

        cards = self._sort_cards(cards, filters.sort)
        if filters.hiring_only:
            cards = [c for c in cards if c.is_hiring]

        paginator = Paginator(cards, filters.page_size)
        page_obj = paginator.get_page(filters.page)

        return InstitutionBrowseResult(
            institutions=list(page_obj.object_list),
            total_count=paginator.count,
            page=page_obj.number,
            page_size=filters.page_size,
            total_pages=paginator.num_pages,
            filter_options=self.filter_options(),
            active_filters=self._active_filters(filters),
        )

    def get_profile(self, slug: str, *, user=None) -> InstitutionProfile | None:
        company = self._get_public_company(slug)
        if company:
            return self._build_company_profile(company, user=user)
        college = self._get_public_college(slug)
        if college:
            return self._build_college_profile(college, user=user)
        return None

    def suggest(self, query: str, *, limit: int = 8) -> list[dict]:
        query = (query or "").strip()
        if len(query) < 2:
            return []
        companies = self._public_companies_qs().filter(
            Q(name__icontains=query)
            | Q(city__icontains=query)
            | Q(industry__icontains=query)
        )[:limit]
        results = [
            {
                "type": "company",
                "label": c.name,
                "sublabel": c.industry or c.city or "IT Company",
                "url": reverse("institution_detail", kwargs={"slug": c.slug}),
            }
            for c in companies
        ]
        remaining = limit - len(results)
        if remaining > 0:
            colleges = self._public_colleges_qs().filter(
                Q(name__icontains=query) | Q(city__icontains=query)
            )[:remaining]
            results.extend(
                {
                    "type": "college",
                    "label": c.name,
                    "sublabel": c.get_institution_type_display()
                    if c.institution_type
                    else "Institution",
                    "url": reverse("institution_detail", kwargs={"slug": c.slug}),
                }
                for c in colleges
            )
        return results

    def filter_options(self) -> dict:
        from apps.companies.constants.enums import CompanySize

        return {
            "domains": [
                {"value": "", "label": "All Domains"},
                {"value": "it", "label": "IT Domain"},
                {"value": "faculty", "label": "Faculty Domain"},
            ],
            "sort_options": [
                {"value": "openings", "label": "Most Open Positions"},
                {"value": "newest", "label": "Newest Institutions"},
                {"value": "name", "label": "Alphabetical"},
                {"value": "active", "label": "Recently Active"},
            ],
            "company_sizes": [
                {"value": c[0], "label": c[1]} for c in CompanySize.choices
            ],
        }

    def _company_cards(self, filters: InstitutionFilterParams) -> list[InstitutionCard]:
        now = timezone.now()
        qs = (
            self._public_companies_qs()
            .annotate(
                active_job_count=Count(
                    "job_postings",
                    filter=self._partners._active_job_q(now),
                    distinct=True,
                )
            )
            .select_related("logo_file", "cover_banner_file")
        )
        qs = self._apply_org_filters(
            qs, filters, city_field="city", industry_field="industry"
        )
        return [self._map_company_card(c) for c in qs]

    def _college_cards(self, filters: InstitutionFilterParams) -> list[InstitutionCard]:
        now = timezone.now()
        qs = (
            self._public_colleges_qs()
            .annotate(
                active_job_count=Count(
                    "vacancies",
                    filter=self._partners._active_vacancy_q(now),
                    distinct=True,
                )
            )
            .select_related("logo_file", "cover_banner_file")
        )
        qs = self._apply_org_filters(
            qs, filters, city_field="city", industry_field=None
        )
        return [self._map_college_card(c) for c in qs]

    def _apply_org_filters(
        self, qs, filters: InstitutionFilterParams, *, city_field, industry_field
    ):
        if filters.q:
            qs = qs.filter(
                Q(name__icontains=filters.q)
                | Q(description__icontains=filters.q)
                | Q(city__icontains=filters.q)
                | Q(state__icontains=filters.q)
            )
        if filters.location:
            qs = qs.filter(
                Q(city__icontains=filters.location)
                | Q(state__icontains=filters.location)
                | Q(**{f"{city_field}__icontains": filters.location})
            )
        if filters.industry and industry_field:
            qs = qs.filter(**{f"{industry_field}__icontains": filters.industry})
        if filters.company_size and hasattr(qs.model, "company_size"):
            qs = qs.filter(company_size=filters.company_size)
        return qs

    def _sort_cards(
        self, cards: list[InstitutionCard], sort: str
    ) -> list[InstitutionCard]:
        if sort == "name":
            return sorted(cards, key=lambda c: c.name.lower())
        if sort == "newest":
            return sorted(
                cards,
                key=lambda c: (c.established_year or 0, c.open_positions),
                reverse=True,
            )
        if sort == "active":
            return sorted(
                cards, key=lambda c: (c.is_hiring, c.open_positions), reverse=True
            )
        return sorted(
            cards,
            key=lambda c: (c.open_positions, c.is_hiring, c.name.lower()),
            reverse=True,
        )

    def _map_company_card(self, company: Company) -> InstitutionCard:
        count = getattr(company, "active_job_count", 0) or 0
        hiring = self._partners._hiring_status(False, False)
        if count > 0:
            hiring = {"hiring_status": "now", "hiring_label": "Currently Hiring"}
        type_label = (
            company.get_organization_type_display()
            if company.organization_type
            else "IT Company"
        )
        employee = company.get_company_size_display() if company.company_size else ""
        desc = (company.description or company.culture or "")[:180]
        return InstitutionCard(
            slug=company.slug,
            name=company.name,
            domain="it",
            domain_label="IT Domain",
            domain_icon="bi-code-slash",
            verified=company.is_verified,
            description=desc,
            location=self._partners._location(company.city, company.state),
            headquarters=company.headquarters_location or company.city or "",
            type_label=type_label,
            established_year=company.founded_year,
            employee_label=employee,
            open_positions=count,
            open_positions_label=self._openings_label(count, "it"),
            is_hiring=count > 0,
            hiring_label=hiring["hiring_label"],
            hiring_status=hiring["hiring_status"],
            logo_url=self._partners._file_url(company.logo_file),
            banner_url=self._partners._file_url(company.cover_banner_file),
            logo_initial=(company.name[:1] or "E").upper(),
            profile_url=reverse("institution_detail", kwargs={"slug": company.slug}),
        )

    def _map_college_card(self, college: College) -> InstitutionCard:
        count = getattr(college, "active_job_count", 0) or 0
        hiring = self._partners._hiring_status(False, False)
        if count > 0:
            hiring = {"hiring_status": "now", "hiring_label": "Currently Hiring"}
        type_label = (
            college.get_institution_type_display()
            if college.institution_type
            else "Institution"
        )
        employee_parts = []
        if college.number_of_faculty:
            employee_parts.append(f"{college.number_of_faculty:,} faculty")
        if college.number_of_students:
            employee_parts.append(f"{college.number_of_students:,} students")
        desc = (college.description or college.infrastructure_description or "")[:180]
        return InstitutionCard(
            slug=college.slug,
            name=college.name,
            domain="faculty",
            domain_label="Faculty Domain",
            domain_icon="bi-mortarboard",
            verified=True,
            description=desc,
            location=self._partners._location(college.city, college.state),
            headquarters=college.city or "",
            type_label=type_label,
            established_year=college.established_year,
            employee_label=" · ".join(employee_parts),
            open_positions=count,
            open_positions_label=self._openings_label(count, "faculty"),
            is_hiring=count > 0,
            hiring_label=hiring["hiring_label"],
            hiring_status=hiring["hiring_status"],
            logo_url=self._partners._file_url(college.logo_file),
            banner_url=self._partners._file_url(college.cover_banner_file),
            logo_initial=(college.name[:1] or "E").upper(),
            profile_url=reverse("institution_detail", kwargs={"slug": college.slug}),
        )

    def _build_company_profile(self, company: Company, *, user) -> InstitutionProfile:
        jobs = self._live_jobs_qs().filter(company=company).order_by("-published_at")
        open_count = jobs.count()
        applicants = sum(j.application_count for j in jobs[:200])
        recruiters = CompanyMember.objects.filter(
            company=company, is_active=True, is_deleted=False
        ).count()
        openings = [self._map_job_opening(j, user=user) for j in jobs[:50]]
        gallery = self._gallery_for_org(company.cover_banner_file, company.logo_file)
        benefits = self._parse_benefits(company.benefits)
        profile_url = reverse("institution_detail", kwargs={"slug": company.slug})

        return InstitutionProfile(
            slug=company.slug,
            name=company.name,
            domain="it",
            domain_label="IT Domain",
            domain_icon="bi-code-slash",
            verified=company.is_verified,
            description=company.description,
            mission=company.mission,
            vision=company.vision,
            culture=company.culture,
            industry=company.industry,
            type_label=company.get_organization_type_display()
            if company.organization_type
            else "IT Company",
            founded_year=company.founded_year,
            headquarters=company.headquarters_location
            or self._partners._location(company.city, company.state),
            address=", ".join(
                p
                for p in [
                    company.address_line,
                    company.city,
                    company.state,
                    company.country,
                ]
                if p
            ),
            website_url=company.website_url,
            email=company.email,
            phone=company.phone,
            company_size_label=company.get_company_size_display()
            if company.company_size
            else "",
            employee_label=company.get_company_size_display()
            if company.company_size
            else "",
            open_positions=open_count,
            recruiter_count=recruiters,
            total_applicants=applicants,
            logo_url=self._partners._file_url(company.logo_file),
            banner_url=self._partners._file_url(company.cover_banner_file),
            logo_initial=(company.name[:1] or "E").upper(),
            benefits=benefits,
            gallery=gallery,
            openings=openings,
            is_hiring=open_count > 0,
            hiring_label="Currently Hiring" if open_count else "No active openings",
            share_url=profile_url,
        )

    def _build_college_profile(self, college: College, *, user) -> InstitutionProfile:
        vacancies = (
            self._live_vacancies_qs().filter(college=college).order_by("-published_at")
        )
        open_count = vacancies.count()
        applicants = sum(v.application_count for v in vacancies[:200])
        members = (
            college.members.filter(is_active=True, is_deleted=False).count()
            if hasattr(college, "members")
            else 0
        )
        openings = [self._map_vacancy_opening(v, user=user) for v in vacancies[:50]]
        gallery = self._gallery_for_org(college.cover_banner_file, college.logo_file)
        benefits = self._parse_benefits(college.facilities)
        employee_parts = []
        if college.number_of_faculty:
            employee_parts.append(f"{college.number_of_faculty:,} faculty members")
        if college.number_of_students:
            employee_parts.append(f"{college.number_of_students:,} students")
        profile_url = reverse("institution_detail", kwargs={"slug": college.slug})

        return InstitutionProfile(
            slug=college.slug,
            name=college.name,
            domain="faculty",
            domain_label="Faculty Domain",
            domain_icon="bi-mortarboard",
            verified=True,
            description=college.description,
            mission=college.mission,
            vision=college.vision,
            culture=college.infrastructure_description,
            industry=college.get_institution_type_display()
            if college.institution_type
            else "",
            type_label=college.get_institution_type_display()
            if college.institution_type
            else "Institution",
            founded_year=college.established_year,
            headquarters=self._partners._location(college.city, college.state),
            address=", ".join(
                p
                for p in [
                    college.address_line,
                    college.city,
                    college.state,
                    college.country,
                ]
                if p
            ),
            website_url=college.website_url,
            email=college.contact_email,
            phone=college.contact_phone,
            company_size_label="",
            employee_label=" · ".join(employee_parts),
            open_positions=open_count,
            recruiter_count=members,
            total_applicants=applicants,
            logo_url=self._partners._file_url(college.logo_file),
            banner_url=self._partners._file_url(college.cover_banner_file),
            logo_initial=(college.name[:1] or "E").upper(),
            benefits=benefits,
            gallery=gallery,
            openings=openings,
            is_hiring=open_count > 0,
            hiring_label="Currently Hiring" if open_count else "No active openings",
            share_url=profile_url,
        )

    def _map_job_opening(self, job: JobPosting, *, user) -> InstitutionOpening:
        is_seeker = self._is_job_seeker(user)
        detail = reverse("marketplace_job_detail", kwargs={"job_id": job.pk})
        apply = (
            detail
            if is_seeker
            else f"{reverse('it_login_job_seeker')}?next={quote(detail, safe='')}"
        )
        return InstitutionOpening(
            id=str(job.pk),
            title=job.title,
            domain="it",
            location=self._mapper._location(
                job.city, job.state, job.is_remote, job.location
            ),
            salary_display=self._mapper._salary(
                job.salary_min, job.salary_max, job.salary_visibility
            ),
            experience_label=self._mapper._experience(job.experience_min),
            work_mode_label=job.get_work_mode_display(),
            employment_type_label=job.get_employment_type_display(),
            posted_display=self._mapper._posted(job.published_at or job.created_at),
            detail_url=detail,
            apply_url=apply,
        )

    def _map_vacancy_opening(
        self, vacancy: FacultyVacancy, *, user
    ) -> InstitutionOpening:
        detail = f"{reverse('institution_detail', kwargs={'slug': vacancy.college.slug})}#opening-{vacancy.pk}"
        apply = f"{reverse('it_login_job_seeker')}?next={quote(detail, safe='')}"
        return InstitutionOpening(
            id=str(vacancy.pk),
            title=vacancy.title,
            domain="faculty",
            location=self._mapper._location(
                vacancy.city, vacancy.state, False, vacancy.campus
            ),
            salary_display=self._mapper._salary(
                vacancy.salary_min, vacancy.salary_max, vacancy.salary_visibility
            ),
            experience_label=self._mapper._experience(vacancy.experience_min),
            work_mode_label=vacancy.get_work_type_display(),
            employment_type_label=vacancy.get_employment_type_display(),
            posted_display=self._mapper._posted(
                vacancy.published_at or vacancy.created_at
            ),
            detail_url=detail,
            apply_url=apply,
        )

    def _get_public_company(self, slug: str) -> Company | None:
        return (
            self._public_companies_qs()
            .filter(slug=slug)
            .select_related("logo_file", "cover_banner_file")
            .first()
        )

    def _get_public_college(self, slug: str) -> College | None:
        return (
            self._public_colleges_qs()
            .filter(slug=slug)
            .select_related("logo_file", "cover_banner_file")
            .prefetch_related("campuses")
            .first()
        )

    def _public_companies_qs(self):
        return Company.objects.filter(
            is_deleted=False,
            is_active=True,
        )

    def _public_colleges_qs(self):
        return College.objects.filter(
            is_deleted=False,
            is_active=True,
        )

    def _live_jobs_qs(self):
        now = timezone.now()
        return JobPosting.objects.filter(
            is_deleted=False,
            status=JobStatus.PUBLISHED,
            visibility=JobVisibility.PUBLIC,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

    def _live_vacancies_qs(self):
        now = timezone.now()
        return FacultyVacancy.objects.filter(
            is_deleted=False,
            status=VacancyStatus.PUBLISHED,
            visibility=VacancyVisibility.PUBLIC,
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))

    @staticmethod
    def _is_job_seeker(user) -> bool:
        return bool(
            user
            and user.is_authenticated
            and RoleAssignmentService().user_has_it_role(
                user, ITUserRoleType.JOB_SEEKER
            )
        )

    @staticmethod
    def _openings_label(count: int, domain: str) -> str:
        if count <= 0:
            return "No open positions"
        if domain == "faculty":
            return f"{count} Active Vacanc{'y' if count == 1 else 'ies'}"
        return f"{count} Open Position{'s' if count != 1 else ''}"

    @staticmethod
    def _parse_benefits(text: str) -> list[str]:
        if not text:
            return []
        normalized = text.replace("•", "\n").replace("|", "\n").replace(";", "\n")
        return [line.strip() for line in normalized.split("\n") if line.strip()][:12]

    @staticmethod
    def _gallery_for_org(banner_file, logo_file) -> list[dict]:
        from apps.reports.selectors.hiring_partners import HiringPartnersSelector

        helper = HiringPartnersSelector()
        items = []
        banner = helper._file_url(banner_file)
        logo = helper._file_url(logo_file)
        if banner:
            items.append({"url": banner, "label": "Cover"})
        if logo:
            items.append({"url": logo, "label": "Logo"})
        return items

    @staticmethod
    def _active_filters(filters: InstitutionFilterParams) -> list[dict]:
        chips = []
        if filters.q:
            chips.append({"key": "q", "label": "Search", "value": filters.q})
        if filters.domain:
            chips.append({"key": "domain", "label": "Domain", "value": filters.domain})
        if filters.location:
            chips.append(
                {"key": "location", "label": "Location", "value": filters.location}
            )
        if filters.industry:
            chips.append(
                {"key": "industry", "label": "Industry", "value": filters.industry}
            )
        if filters.hiring_only:
            chips.append({"key": "hiring_only", "label": "Hiring", "value": "Yes"})
        return chips
