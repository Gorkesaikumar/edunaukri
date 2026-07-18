from django.db.models import Q
from django.utils import timezone

from apps.core.selectors.read import ReadSelector
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy


def _not_expired(queryset):
    now = timezone.now()
    return queryset.filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))


class FacultyVacancySelector(ReadSelector):
    model = FacultyVacancy
    search_fields = ("title", "college_name_snapshot", "vacancy_code", "department")

    def get_or_none(self, vacancy_id):
        return self.filter_by(pk=vacancy_id).select_related("college").first()

    def published(self, *, search: str | None = None):
        queryset = _not_expired(self.filter_by(status=VacancyStatus.PUBLISHED)).select_related(
            "college"
        )
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.order_by("-published_at")

    def get_published_by_id(self, vacancy_id):
        return _not_expired(
            self.filter_by(pk=vacancy_id, status=VacancyStatus.PUBLISHED)
        ).first()

    def for_college_user(self, college_user, *, status: str | None = None):
        from apps.colleges.selectors.college_selector import CollegeMemberSelector

        college_ids = (
            CollegeMemberSelector()
            .for_user(college_user)
            .values_list("college_id", flat=True)
        )
        queryset = self.filter_by(college_id__in=college_ids).select_related("college")
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def templates(self, college_user):
        from apps.colleges.selectors.college_selector import CollegeMemberSelector

        college_ids = (
            CollegeMemberSelector()
            .for_user(college_user)
            .values_list("college_id", flat=True)
        )
        return self.filter_by(college_id__in=college_ids, is_template=True).select_related(
            "college"
        ).order_by(
            "-created_at"
        )

    def admin_list(
        self, *, status: str | None = None, college_id=None, search: str | None = None
    ):
        queryset = self.filter_by().select_related("college")
        if status:
            queryset = queryset.filter(status=status)
        if college_id:
            queryset = queryset.filter(college_id=college_id)
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.order_by("-created_at")


class CollegeVacancySelector(ReadSelector):
    """Read scope limited to a single college's vacancies."""

    model = FacultyVacancy

    def for_college(self, college_id, *, status: str | None = None):
        queryset = self.filter_by(college_id=college_id).select_related("college")
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-created_at")

    def published_for_college(self, college_id):
        return self.for_college(college_id, status=VacancyStatus.PUBLISHED)


class PublicFacultyVacancySelector(ReadSelector):
    """Read scope for professor / anonymous discovery of published vacancies."""

    model = FacultyVacancy

    def published(self):
        return (
            _not_expired(self.filter_by(status=VacancyStatus.PUBLISHED))
            .select_related("college")
            .order_by("-published_at")
        )

    def get_published(self, vacancy_id):
        return (
            _not_expired(self.filter_by(pk=vacancy_id, status=VacancyStatus.PUBLISHED))
            .select_related("college")
            .first()
        )
