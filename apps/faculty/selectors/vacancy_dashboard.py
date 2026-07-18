from apps.core.selectors.read import ReadSelector
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_selector import (
    CollegeVacancySelector,
    FacultyVacancySelector,
)


class VacancyDashboardSelector(ReadSelector):
    model = FacultyVacancy

    def _summarize(self, queryset) -> dict:
        by_status = {
            choice.value: queryset.filter(status=choice.value).count()
            for choice in VacancyStatus
        }
        return {
            "total_vacancies": queryset.count(),
            "published_vacancies": by_status.get(VacancyStatus.PUBLISHED, 0),
            "draft_vacancies": by_status.get(VacancyStatus.DRAFT, 0),
            "featured_vacancies": queryset.filter(
                status=VacancyStatus.PUBLISHED, is_featured=True
            ).count(),
            "urgent_vacancies": queryset.filter(
                status=VacancyStatus.PUBLISHED, is_urgent=True
            ).count(),
            "vacancies_by_status": by_status,
        }

    def college_user_summary(self, college_user) -> dict:
        return self._summarize(FacultyVacancySelector().for_college_user(college_user))

    def college_summary(self, college_id) -> dict:
        return self._summarize(CollegeVacancySelector().for_college(college_id))

    def platform_summary(self) -> dict:
        return self._summarize(self.filter_by())

    def vacancy_statistics(self, vacancy: FacultyVacancy) -> dict:
        return {
            "vacancy_id": str(vacancy.pk),
            "title": vacancy.title,
            "status": vacancy.status,
            "application_count": vacancy.application_count,
            "view_count": vacancy.view_count,
            "vacancy_count": vacancy.vacancy_count,
            "is_featured": vacancy.is_featured,
            "is_urgent": vacancy.is_urgent,
            "published_at": vacancy.published_at,
            "expires_at": vacancy.expires_at,
        }
