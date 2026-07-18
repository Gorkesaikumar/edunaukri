"""Institution vacancy management portal — list, stats, and lifecycle URLs."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models.college_user import CollegeUser
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication
from apps.authentication.services.portal_url_service import PortalURLService
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import VacancyStatus, WorkType
from apps.faculty.services.faculty_vacancy_service import EDITABLE_STATUSES
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.it_recruitment.services.jobseeker_portal_helpers import format_salary_lpa


@dataclass
class CollegeVacanciesPortalContext:
    vacancies: list[dict]
    stats: dict
    has_institution: bool
    can_publish: bool
    institution: dict | None
    pagination: dict
    filters: dict
    status_options: list[dict]
    api_urls: dict


class CollegeVacanciesPortalService(BaseService):
    PER_PAGE = 15

    STATUS_FILTERS = [
        {"key": "", "label": "All"},
        {"key": VacancyStatus.PUBLISHED, "label": "Published"},
        {"key": VacancyStatus.DRAFT, "label": "Drafts"},
        {"key": VacancyStatus.PAUSED, "label": "Paused"},
        {"key": VacancyStatus.CLOSED, "label": "Closed"},
        {"key": VacancyStatus.ARCHIVED, "label": "Archived"},
    ]

    def build(
        self,
        user: CollegeUser,
        *,
        status_filter: str = "",
        q: str = "",
        page: int = 1,
    ) -> CollegeVacanciesPortalContext:
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        from apps.academic_recruitment.services.college_portal_helpers import (
            primary_institution_for_user,
        )

        institution = primary_institution_for_user(user)
        has_institution = CollegeMemberSelector().has_active_membership(user)
        can_publish = bool(institution and institution.get("can_publish"))

        queryset = (
            FacultyVacancySelector()
            .for_college_user(user)
            .select_related("college")
            .order_by("-published_at", "-created_at")
        )
        if status_filter and status_filter in VacancyStatus.values:
            queryset = queryset.filter(status=status_filter)
        if q:
            queryset = queryset.filter(
                Q(title__icontains=q)
                | Q(department__icontains=q)
                | Q(city__icontains=q)
                | Q(college_name_snapshot__icontains=q)
            )

        paginator = Paginator(queryset, self.PER_PAGE)
        page_obj = paginator.get_page(page)
        vacancy_ids = [v.pk for v in page_obj.object_list]
        metrics = self._bulk_metrics(vacancy_ids)

        vacancies = [
            self._serialize_vacancy(v, pu, metrics.get(str(v.pk), {}))
            for v in page_obj.object_list
        ]

        all_vacancies = FacultyVacancySelector().for_college_user(user)
        stats = {
            "total": all_vacancies.count(),
            "published": all_vacancies.filter(status=VacancyStatus.PUBLISHED).count(),
            "draft": all_vacancies.filter(status=VacancyStatus.DRAFT).count(),
            "paused": all_vacancies.filter(status=VacancyStatus.PAUSED).count(),
            "closed": all_vacancies.filter(status=VacancyStatus.CLOSED).count(),
            "archived": all_vacancies.filter(status=VacancyStatus.ARCHIVED).count(),
        }

        return CollegeVacanciesPortalContext(
            vacancies=vacancies,
            stats=stats,
            has_institution=has_institution,
            can_publish=can_publish,
            institution=institution,
            pagination={
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
                "start_index": page_obj.start_index() if paginator.count else 0,
                "end_index": page_obj.end_index() if paginator.count else 0,
            },
            filters={"q": q, "status": status_filter},
            status_options=self.STATUS_FILTERS,
            api_urls=self._api_urls(pu),
        )

    @staticmethod
    def _api_urls(pu) -> dict:
        placeholder = "00000000-0000-0000-0000-000000000000"
        return {
            "list": pu("college_vacancies_list_api"),
            "publish_template": pu(
                "college_vacancy_publish_api", vacancy_id=placeholder
            ),
            "pause_template": pu("college_vacancy_pause_api", vacancy_id=placeholder),
            "close_template": pu("college_vacancy_close_api", vacancy_id=placeholder),
            "reopen_template": pu("college_vacancy_reopen_api", vacancy_id=placeholder),
            "duplicate_template": pu(
                "college_vacancy_duplicate_api", vacancy_id=placeholder
            ),
            "archive_template": pu(
                "college_vacancy_archive_api", vacancy_id=placeholder
            ),
            "delete_template": pu("college_vacancy_delete_api", vacancy_id=placeholder),
            "status_template": pu(
                "college_application_status_api", application_id=placeholder
            ),
            "notes_template": pu(
                "college_application_notes_api", application_id=placeholder
            ),
        }

    @staticmethod
    def _bulk_metrics(vacancy_ids: list) -> dict[str, dict[str, int]]:
        if not vacancy_ids:
            return {}
        rows = (
            FacultyApplication.objects.filter(
                vacancy_id__in=vacancy_ids, is_deleted=False
            )
            .values("vacancy_id", "status")
            .annotate(c=Count("id"))
        )
        metrics: dict[str, dict[str, int]] = {}
        for row in rows:
            vid = str(row["vacancy_id"])
            metrics.setdefault(vid, {})
            metrics[vid][row["status"]] = row["c"]
        return metrics

    @classmethod
    def _serialize_vacancy(
        cls,
        vacancy: FacultyVacancy,
        pu,
        metrics: dict[str, int] | None = None,
    ) -> dict:
        metrics = metrics or {}
        total_apps = sum(metrics.values()) or vacancy.application_count
        shortlisted = sum(
            metrics.get(s, 0)
            for s in (
                FacultyApplicationStatus.DEPARTMENT_REVIEW,
                FacultyApplicationStatus.PRINCIPAL_REVIEW,
                FacultyApplicationStatus.MANAGEMENT_APPROVAL,
            )
        )
        interviews = metrics.get(
            FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0
        ) + metrics.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0)
        offers = metrics.get(FacultyApplicationStatus.OFFER_RELEASED, 0) + metrics.get(
            FacultyApplicationStatus.OFFER_ACCEPTED, 0
        )
        joined = metrics.get(FacultyApplicationStatus.JOINED, 0)

        published_label = (
            timezone.localtime(vacancy.published_at).strftime("%b %d, %Y")
            if vacancy.published_at
            else "—"
        )
        college = vacancy.college

        return {
            "id": str(vacancy.pk),
            "title": vacancy.title,
            "department": vacancy.department or "—",
            "designation": vacancy.get_designation_display()
            if vacancy.designation
            else "—",
            "employment_type": vacancy.get_employment_type_display(),
            "work_type": cls._work_type_label(vacancy),
            "location": vacancy.city or vacancy.college_name_snapshot or "—",
            "salary_range": format_salary_lpa(
                vacancy.salary_min, vacancy.salary_max, vacancy.salary_currency
            ),
            "experience_label": cls._experience_label(vacancy),
            "status": vacancy.status,
            "status_label": vacancy.get_status_display(),
            "status_tone": cls._status_tone(vacancy.status),
            "application_count": total_apps,
            "shortlisted_count": shortlisted,
            "interview_count": interviews,
            "offer_count": offers,
            "joined_count": joined,
            "view_count": vacancy.view_count,
            "published_label": published_label,
            "created_label": timezone.localtime(vacancy.created_at).strftime(
                "%b %d, %Y"
            ),
            "applications_url": pu("college_applications")
            + f"?vacancy_id={vacancy.pk}",
            "edit_url": pu("college_vacancy_edit", vacancy_id=vacancy.pk),
            "publish_url": pu("college_vacancy_publish_api", vacancy_id=vacancy.pk),
            "close_url": pu("college_vacancy_close_api", vacancy_id=vacancy.pk),
            "pause_url": pu("college_vacancy_pause_api", vacancy_id=vacancy.pk),
            "reopen_url": pu("college_vacancy_reopen_api", vacancy_id=vacancy.pk),
            "duplicate_url": pu("college_vacancy_duplicate_api", vacancy_id=vacancy.pk),
            "archive_url": pu("college_vacancy_archive_api", vacancy_id=vacancy.pk),
            "delete_url": pu("college_vacancy_delete_api", vacancy_id=vacancy.pk),
            "can_publish": vacancy.status
            in (
                VacancyStatus.DRAFT,
                VacancyStatus.PENDING_APPROVAL,
                VacancyStatus.PAUSED,
            )
            and college.can_publish_vacancies,
            "can_edit": vacancy.status in EDITABLE_STATUSES,
            "can_close": vacancy.status
            in (
                VacancyStatus.DRAFT,
                VacancyStatus.PUBLISHED,
                VacancyStatus.PAUSED,
                VacancyStatus.PENDING_APPROVAL,
            ),
            "can_pause": vacancy.status == VacancyStatus.PUBLISHED,
            "can_reopen": vacancy.status in (VacancyStatus.PAUSED, VacancyStatus.CLOSED)
            and college.can_publish_vacancies,
            "can_duplicate": True,
            "can_archive": vacancy.status
            in (VacancyStatus.CLOSED, VacancyStatus.EXPIRED, VacancyStatus.PAUSED),
            "can_delete": vacancy.status
            in (
                VacancyStatus.DRAFT,
                VacancyStatus.CLOSED,
                VacancyStatus.PAUSED,
                VacancyStatus.ARCHIVED,
            ),
        }

    @staticmethod
    def _work_type_label(vacancy: FacultyVacancy) -> str:
        if vacancy.work_type == WorkType.REMOTE:
            return "Remote"
        if vacancy.work_type == WorkType.HYBRID:
            return "Hybrid"
        return vacancy.get_work_type_display() if vacancy.work_type else "Onsite"

    @staticmethod
    def _experience_label(vacancy: FacultyVacancy) -> str:
        if vacancy.experience_min is not None and vacancy.experience_max is not None:
            return f"{vacancy.experience_min}–{vacancy.experience_max} yrs"
        if vacancy.experience_min is not None:
            return f"{vacancy.experience_min}+ yrs"
        if vacancy.experience_max is not None:
            return f"Up to {vacancy.experience_max} yrs"
        return "—"

    @staticmethod
    def _status_tone(status: str) -> str:
        tones = {
            VacancyStatus.PUBLISHED: "success",
            VacancyStatus.DRAFT: "muted",
            VacancyStatus.PAUSED: "warning",
            VacancyStatus.CLOSED: "danger",
            VacancyStatus.ARCHIVED: "muted",
            VacancyStatus.EXPIRED: "warning",
            VacancyStatus.PENDING_APPROVAL: "info",
        }
        return tones.get(status, "primary")
