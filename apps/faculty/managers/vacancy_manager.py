"""Model managers for the Faculty Vacancy Management module."""

from apps.core.managers import ActiveManager, SoftDeleteQuerySet
from apps.faculty.constants.enums import VacancyStatus


class FacultyVacancyQuerySet(SoftDeleteQuerySet):
    def published(self):
        return self.filter(status=VacancyStatus.PUBLISHED)

    def drafts(self):
        return self.filter(status=VacancyStatus.DRAFT)

    def live(self):
        return self.filter(status=VacancyStatus.PUBLISHED)

    def featured(self):
        return self.filter(status=VacancyStatus.PUBLISHED, is_featured=True)

    def urgent(self):
        return self.filter(status=VacancyStatus.PUBLISHED, is_urgent=True)

    def for_college(self, college_id):
        return self.filter(college_id=college_id)


class FacultyVacancyManager(ActiveManager.from_queryset(FacultyVacancyQuerySet)):
    """Default manager returning only non-deleted vacancies with domain scopes."""
