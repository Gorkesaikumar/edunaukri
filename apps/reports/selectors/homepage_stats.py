"""Read-side aggregation of public platform statistics for the landing page.

Each call recomputes counts directly from the database so the marketing
homepage always reflects real-time platform activity.
"""

from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication, JobApplication
from apps.colleges.models import College
from apps.companies.models import Company
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.models import FacultyVacancy
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting


class HomepageStatsSelector:
    """Compose public-facing platform KPIs for the homepage hero stat cards."""

    def public_stats(self) -> dict:
        active_jobs = self._active_jobs()
        institutions = self._institutions()
        hiring_success_pct = self._hiring_success_pct()
        verified_employers = self._verified_employers()

        return {
            "active_jobs": active_jobs,
            "institutions": institutions,
            "hiring_success_pct": hiring_success_pct,
            "verified_employers": verified_employers,
        }

    def _active_jobs(self) -> int:
        return (
            JobPosting.objects.filter(
                is_deleted=False, status=JobStatus.PUBLISHED
            ).count()
            + FacultyVacancy.objects.filter(
                is_deleted=False, status=VacancyStatus.PUBLISHED
            ).count()
        )

    def _institutions(self) -> int:
        return College.objects.filter(is_deleted=False).count()

    def _hiring_success_pct(self) -> float:
        it_total = JobApplication.objects.filter(is_deleted=False).count()
        it_hired = JobApplication.objects.filter(
            is_deleted=False, status=JobApplicationStatus.HIRED
        ).count()
        faculty_total = FacultyApplication.objects.filter(is_deleted=False).count()
        faculty_joined = FacultyApplication.objects.filter(
            is_deleted=False, status=FacultyApplicationStatus.JOINED
        ).count()

        total = it_total + faculty_total
        successful = it_hired + faculty_joined
        if not total:
            return 0.0
        return round(100 * successful / total, 1)

    def _verified_employers(self) -> int:
        return (
            Company.objects.filter(is_deleted=False).count()
            + College.objects.filter(is_deleted=False).count()
        )
