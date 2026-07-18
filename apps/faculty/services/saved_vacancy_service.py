"""Saved faculty vacancies — toggle, count, list, and status for professor portal."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone

from apps.academic_recruitment.models import ProfessorProfile
from apps.authentication.services.portal_url_service import PortalURLService
from apps.core.services.base import BaseService
from apps.faculty.models import FacultyVacancy, SavedVacancy
from apps.faculty.selectors.vacancy_selector import PublicFacultyVacancySelector
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_salary_lpa,
    media_url,
)


@dataclass
class SavedVacancyCard:
    id: str
    saved_id: str
    title: str
    institution_name: str
    location: str
    logo_url: str | None
    tags: list[str]
    saved_at_display: str
    detail_url: str
    apply_url: str
    save_url: str
    is_open: bool

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "saved_id": self.saved_id,
            "title": self.title,
            "institution_name": self.institution_name,
            "location": self.location,
            "logo_url": self.logo_url,
            "tags": self.tags,
            "saved_at_display": self.saved_at_display,
            "detail_url": self.detail_url,
            "apply_url": self.apply_url,
            "save_url": self.save_url,
            "is_open": self.is_open,
        }


@dataclass
class SavedVacancyListResult:
    vacancies: list[SavedVacancyCard]
    total_count: int
    page: int
    page_size: int
    total_pages: int


@dataclass
class SavedVacancyToggleResult:
    vacancy_id: str
    is_saved: bool
    saved_count: int
    message: str

    def to_dict(self) -> dict:
        return {
            "vacancy_id": self.vacancy_id,
            "is_saved": self.is_saved,
            "saved_count": self.saved_count,
            "message": self.message,
        }


class SavedVacancyService(BaseService):
    def count(self, profile: ProfessorProfile) -> int:
        return SavedVacancy.objects.filter(professor=profile, is_deleted=False).count()

    @transaction.atomic
    def toggle(self, profile: ProfessorProfile, vacancy_id) -> SavedVacancyToggleResult:
        vacancy = PublicFacultyVacancySelector().get_published(vacancy_id)
        if not vacancy:
            raise ValueError("Vacancy not found or no longer available.")

        existing = SavedVacancy.all_objects.filter(
            professor=profile, vacancy=vacancy
        ).first()
        if existing and not existing.is_deleted:
            existing.delete()
            return SavedVacancyToggleResult(
                vacancy_id=str(vacancy.pk),
                is_saved=False,
                saved_count=self.count(profile),
                message="Vacancy removed from saved jobs.",
            )

        if existing and existing.is_deleted:
            existing.restore()
        else:
            SavedVacancy.objects.create(
                professor=profile,
                vacancy=vacancy,
                created_by_id=profile.user_id,
            )
        return SavedVacancyToggleResult(
            vacancy_id=str(vacancy.pk),
            is_saved=True,
            saved_count=self.count(profile),
            message="Vacancy saved successfully.",
        )

    def status_map(
        self, profile: ProfessorProfile, vacancy_ids: list[str]
    ) -> dict[str, bool]:
        if not vacancy_ids:
            return {}
        saved = {
            str(vid)
            for vid in SavedVacancy.objects.filter(
                professor=profile,
                vacancy_id__in=vacancy_ids,
                is_deleted=False,
            ).values_list("vacancy_id", flat=True)
        }
        return {vid: str(vid) in saved for vid in vacancy_ids}

    def list_saved(
        self,
        profile: ProfessorProfile,
        *,
        page: int = 1,
        page_size: int = 12,
    ) -> SavedVacancyListResult:
        qs = (
            SavedVacancy.objects.filter(professor=profile, is_deleted=False)
            .select_related(
                "vacancy", "vacancy__college", "vacancy__college__logo_file"
            )
            .order_by("-created_at")
        )
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        cards = [self._map_card(row, profile) for row in page_obj.object_list]
        return SavedVacancyListResult(
            vacancies=cards,
            total_count=paginator.count,
            page=page_obj.number,
            page_size=page_size,
            total_pages=paginator.num_pages,
        )

    def _map_card(
        self, saved: SavedVacancy, profile: ProfessorProfile
    ) -> SavedVacancyCard:
        vacancy = saved.vacancy
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
        employment = (
            vacancy.get_employment_type_display()
            if vacancy.employment_type
            else "Full-time"
        )
        tags = [t for t in [salary, employment] if t and t != "Not disclosed"]
        pu = lambda name, **kw: PortalURLService.professor(profile.user, name, **kw)

        return SavedVacancyCard(
            id=str(vacancy.pk),
            saved_id=str(saved.pk),
            title=vacancy.title,
            institution_name=vacancy.college_name_snapshot
            or (college.name if college else ""),
            location=location,
            logo_url=logo,
            tags=tags,
            saved_at_display=timezone.localtime(saved.created_at).strftime("%b %d, %Y"),
            detail_url=pu("professor_vacancy_detail", vacancy_id=vacancy.pk),
            apply_url=pu("professor_apply_vacancy", vacancy_id=vacancy.pk),
            save_url=pu("professor_save_vacancy", vacancy_id=vacancy.pk),
            is_open=not vacancy.is_deleted,
        )
