from django.db.models import Count, Q

from apps.applications.models import FacultyApplication, JobApplication
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.selectors.read import ReadSelector


class JobApplicationSelector(ReadSelector):
    model = JobApplication
    search_fields = (
        "applicant_name_snapshot",
        "job_title_snapshot",
        "company_name_snapshot",
        "current_location",
    )

    def for_seeker(self, job_seeker, *, status: str | None = None):
        queryset = self.filter_by(job_seeker=job_seeker).select_related(
            "job_posting", "company", "resume_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-applied_at")

    def for_job_posting(self, job_posting, *, status: str | None = None):
        queryset = self.filter_by(job_posting=job_posting).select_related("job_seeker", "resume_file")
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-applied_at")

    def for_recruiter(self, recruiter, *, status: str | None = None):
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        queryset = self.filter_by(
            job_posting__company_id__in=company_ids
        ).select_related("job_posting", "job_seeker", "resume_file")
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-applied_at")

    def for_company(
        self, company_id, *, status: str | None = None, job_posting_id=None
    ):
        queryset = self.filter_by(company_id=company_id).select_related(
            "job_posting", "job_seeker", "resume_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        if job_posting_id:
            queryset = queryset.filter(job_posting_id=job_posting_id)
        return queryset.order_by("-applied_at")

    def get_active(self, application_id):
        return (
            self.filter_by(pk=application_id)
            .select_related("job_posting", "job_seeker", "job_seeker__user", "company", "resume_file")
            .first()
        )

    def admin_list(
        self,
        *,
        status: str | None = None,
        job_posting_id=None,
        company_id=None,
        search: str | None = None,
    ):
        queryset = self.filter_by().select_related(
            "job_posting", "job_seeker", "job_seeker__user", "resume_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        if job_posting_id:
            queryset = queryset.filter(job_posting_id=job_posting_id)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if search:
            queryset = queryset.filter(
                Q(applicant_name_snapshot__icontains=search)
                | Q(job_title_snapshot__icontains=search)
                | Q(company_name_snapshot__icontains=search)
            )
        return queryset.order_by("-applied_at")


# Canonical aliases from the module spec.
RecruiterApplicationSelector = JobApplicationSelector


class CandidateApplicationSelector(ReadSelector):
    model = JobApplication

    def for_seeker(self, job_seeker, *, status: str | None = None):
        return JobApplicationSelector().for_seeker(job_seeker, status=status)


class ApplicationStatisticsSelector(ReadSelector):
    model = JobApplication

    def count_by_status(self, queryset=None):
        queryset = queryset if queryset is not None else self.filter_by()
        return dict(
            queryset.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )


class ApplicationSearchSelector(ReadSelector):
    """PostgreSQL-backed application search for recruiters and admins."""

    model = JobApplication

    def search(
        self,
        *,
        query: str = "",
        status: str = "",
        company_id=None,
        job_posting_id=None,
        job_seeker_id=None,
        recruiter=None,
        sort: str = "recent",
    ):
        qs = self.filter_by().select_related("job_posting", "job_seeker", "company", "resume_file")

        if recruiter:
            company_ids = (
                CompanyMemberSelector()
                .for_recruiter(recruiter)
                .values_list("company_id", flat=True)
            )
            qs = qs.filter(job_posting__company_id__in=company_ids)
        if query:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=query)
                | Q(job_title_snapshot__icontains=query)
                | Q(company_name_snapshot__icontains=query)
                | Q(current_location__icontains=query)
            )
        if status:
            qs = qs.filter(status=status)
        if company_id:
            qs = qs.filter(company_id=company_id)
        if job_posting_id:
            qs = qs.filter(job_posting_id=job_posting_id)
        if job_seeker_id:
            qs = qs.filter(job_seeker_id=job_seeker_id)

        order_map = {
            "recent": "-applied_at",
            "oldest": "applied_at",
            "status": "status",
        }
        return qs.order_by(order_map.get(sort, "-applied_at"))


class FacultyApplicationSelector(ReadSelector):
    model = FacultyApplication
    search_fields = (
        "applicant_name_snapshot",
        "vacancy_title_snapshot",
        "college_name_snapshot",
        "department",
        "current_institution",
    )

    def for_professor(self, professor, *, status: str | None = None):
        queryset = self.filter_by(professor=professor).select_related(
            "vacancy", "college", "cv_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-applied_at")

    def for_vacancy(self, vacancy, *, status: str | None = None):
        queryset = self.filter_by(vacancy=vacancy).select_related("professor", "cv_file")
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-applied_at")

    def for_college_user(self, college_user, *, status: str | None = None):
        college_ids = (
            CollegeMemberSelector()
            .for_user(college_user)
            .values_list("college_id", flat=True)
        )
        queryset = self.filter_by(vacancy__college_id__in=college_ids).select_related(
            "vacancy", "professor", "cv_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by("-applied_at")

    def for_college(
        self,
        college_id,
        *,
        status: str | None = None,
        vacancy_id=None,
        department: str | None = None,
    ):
        queryset = self.filter_by(college_id=college_id).select_related(
            "vacancy", "professor", "cv_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        if vacancy_id:
            queryset = queryset.filter(vacancy_id=vacancy_id)
        if department:
            queryset = queryset.filter(department__icontains=department)
        return queryset.order_by("-applied_at")

    def get_active(self, application_id):
        return (
            self.filter_by(pk=application_id)
            .select_related("vacancy", "professor", "professor__user", "college", "cv_file")
            .first()
        )

    def admin_list(
        self,
        *,
        status: str | None = None,
        vacancy_id=None,
        college_id=None,
        search: str | None = None,
    ):
        queryset = self.filter_by().select_related(
            "vacancy", "professor", "professor__user", "college", "cv_file"
        )
        if status:
            queryset = queryset.filter(status=status)
        if vacancy_id:
            queryset = queryset.filter(vacancy_id=vacancy_id)
        if college_id:
            queryset = queryset.filter(college_id=college_id)
        if search:
            queryset = queryset.filter(
                Q(applicant_name_snapshot__icontains=search)
                | Q(vacancy_title_snapshot__icontains=search)
                | Q(college_name_snapshot__icontains=search)
            )
        return queryset.order_by("-applied_at")


CollegeApplicationSelector = FacultyApplicationSelector


class ProfessorApplicationSelector(ReadSelector):
    model = FacultyApplication

    def for_professor(self, professor, *, status: str | None = None):
        return FacultyApplicationSelector().for_professor(professor, status=status)


class FacultyApplicationStatisticsSelector(ReadSelector):
    model = FacultyApplication

    def count_by_status(self, queryset=None):
        queryset = queryset if queryset is not None else self.filter_by()
        return dict(
            queryset.values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )


class FacultyApplicationSearchSelector(ReadSelector):
    """PostgreSQL-backed faculty application search for colleges and admins."""

    model = FacultyApplication

    def search(
        self,
        *,
        query: str = "",
        status: str = "",
        college_id=None,
        vacancy_id=None,
        professor_id=None,
        department: str = "",
        college_user=None,
        sort: str = "recent",
    ):
        qs = self.filter_by().select_related("vacancy", "professor", "college", "cv_file")

        if college_user:
            college_ids = (
                CollegeMemberSelector()
                .for_user(college_user)
                .values_list("college_id", flat=True)
            )
            qs = qs.filter(vacancy__college_id__in=college_ids)
        if query:
            qs = qs.filter(
                Q(applicant_name_snapshot__icontains=query)
                | Q(vacancy_title_snapshot__icontains=query)
                | Q(college_name_snapshot__icontains=query)
                | Q(department__icontains=query)
                | Q(current_institution__icontains=query)
            )
        if status:
            qs = qs.filter(status=status)
        if college_id:
            qs = qs.filter(college_id=college_id)
        if vacancy_id:
            qs = qs.filter(vacancy_id=vacancy_id)
        if professor_id:
            qs = qs.filter(professor_id=professor_id)
        if department:
            qs = qs.filter(department__icontains=department)

        order_map = {
            "recent": "-applied_at",
            "oldest": "applied_at",
            "status": "status",
        }
        return qs.order_by(order_map.get(sort, "-applied_at"))
