from django.db.models import F

from apps.core.repositories.crud import CRUDRepository, ReadRepository
from apps.faculty.models import FacultyVacancy, FacultyVacancyCampus


class FacultyVacancyReadRepository(ReadRepository):
    model = FacultyVacancy


class FacultyVacancyRepository(CRUDRepository):
    model = FacultyVacancy
    search_fields = ("title", "college_name_snapshot", "vacancy_code", "department")

    def increment_application_count(self, vacancy: FacultyVacancy) -> None:
        self.filter_by(pk=vacancy.pk).update(
            application_count=F("application_count") + 1
        )

    def increment_view_count(self, vacancy: FacultyVacancy) -> None:
        self.filter_by(pk=vacancy.pk).update(view_count=F("view_count") + 1)


class FacultyVacancyCampusRepository(CRUDRepository):
    model = FacultyVacancyCampus
