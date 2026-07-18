"""Browse published faculty vacancies inside the professor portal."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.db.models import Q

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_portal_helpers import (
    institution_profile_url,
)
from apps.applications.models import FacultyApplication
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_selector import PublicFacultyVacancySelector
from apps.faculty.services.saved_vacancy_service import SavedVacancyService
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    media_url,
)


@dataclass
class BrowseVacancyCard:
    id: str
    title: str
    institution_name: str
    location: str
    logo_url: str | None
    tags: list[str]
    posted_display: str
    detail_url: str
    apply_url: str
    is_saved: bool
    has_applied: bool
    application_id: str | None = None
    application_detail_url: str | None = None
    application_status: str | None = None
    institution_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "institution_name": self.institution_name,
            "location": self.location,
            "logo_url": self.logo_url,
            "tags": self.tags,
            "posted_display": self.posted_display,
            "detail_url": self.detail_url,
            "apply_url": self.apply_url,
            "is_saved": self.is_saved,
            "has_applied": self.has_applied,
            "application_id": self.application_id,
            "application_detail_url": self.application_detail_url,
            "application_status": self.application_status,
            "institution_url": self.institution_url,
        }


@dataclass
class ProfessorBrowsePageContext:
    vacancies: list[BrowseVacancyCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters: dict

    def to_template_dict(self) -> dict:
        return {
            "vacancies": [v.to_dict() for v in self.vacancies],
            "total_count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "filters": self.filters,
        }


class ProfessorBrowsePortalService(BaseService):
    PAGE_SIZE = 12

    def list_vacancies(
        self,
        profile: ProfessorProfile | None,
        *,
        page: int = 1,
        q: str = "",
        department: str = "",
        city: str = "",
    ) -> ProfessorBrowsePageContext:
        queryset = (
            PublicFacultyVacancySelector()
            .published()
            .select_related("college", "college__logo_file")
        )

        q = (q or "").strip()
        department = (department or "").strip()
        city = (city or "").strip()

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(college_name_snapshot__icontains=q)
                | Q(department__icontains=q)
                | Q(city__icontains=q)
                | Q(specialization_required__icontains=q)
            )
        if department:
            queryset = queryset.filter(department__icontains=department)
        if city:
            queryset = queryset.filter(city__icontains=city)

        paginator = Paginator(queryset, self.PAGE_SIZE)
        page_obj = paginator.get_page(page)
        vacancy_ids = [str(v.pk) for v in page_obj.object_list]
        saved_map = (
            SavedVacancyService().status_map(profile, vacancy_ids) if profile else {}
        )
        application_map: dict[str, FacultyApplication] = {}
        if profile:
            for app in profile.applications.filter(
                vacancy_id__in=vacancy_ids, is_deleted=False
            ):
                application_map[str(app.vacancy_id)] = app

        cards = [
            self._map_card(
                v,
                profile,
                saved_map.get(str(v.pk), False),
                application_map.get(str(v.pk)),
            )
            for v in page_obj.object_list
        ]

        return ProfessorBrowsePageContext(
            vacancies=cards,
            total_count=paginator.count,
            page=page_obj.number,
            page_size=self.PAGE_SIZE,
            total_pages=paginator.num_pages,
            filters={"q": q, "department": department, "city": city},
        )

    def _map_card(
        self,
        vacancy: FacultyVacancy,
        profile: ProfessorProfile | None,
        is_saved: bool,
        application: FacultyApplication | None,
    ) -> BrowseVacancyCard:
        college = vacancy.college if vacancy.college_id else None
        logo = (
            media_url(college.logo_file) if college and college.logo_file_id else None
        )
        location = (
            ", ".join(p for p in [vacancy.city, vacancy.state] if p)
            or "Location not specified"
        )
        salary = (
            format_salary_lpa(
                vacancy.salary_min, vacancy.salary_max, vacancy.salary_currency or "INR"
            )
            if vacancy.salary_min or vacancy.salary_max
            else None
        )
        tags = [
            t
            for t in [vacancy.department, salary, vacancy.get_employment_type_display()]
            if t
        ]
        posted = vacancy.published_at or vacancy.created_at
        posted_display = posted.strftime("%b %d, %Y") if posted else "—"
        pu = lambda name, **kw: (
            PortalURLService.professor(profile.user, name, **kw) if profile else ""
        )
        app_status = None
        app_detail_url = None
        app_id = None
        if application is not None:
            app_id = str(application.pk)
            app_status = application.get_status_display()
            app_detail_url = pu(
                "professor_application_detail", application_id=application.pk
            )

        return BrowseVacancyCard(
            id=str(vacancy.pk),
            title=vacancy.title,
            institution_name=vacancy.college_name_snapshot
            or (college.name if college else ""),
            location=location,
            logo_url=logo,
            tags=tags,
            posted_display=posted_display,
            detail_url=pu("professor_vacancy_detail", vacancy_id=vacancy.pk),
            apply_url=pu("professor_apply_vacancy", vacancy_id=vacancy.pk),
            is_saved=is_saved,
            has_applied=application is not None,
            application_id=app_id,
            application_detail_url=app_detail_url,
            application_status=app_status,
            institution_url=institution_profile_url(college),
        )
