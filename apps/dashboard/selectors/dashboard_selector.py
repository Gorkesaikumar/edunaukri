from django.core.cache import cache
from django.db.models import Count

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.applications.models import FacultyApplication, JobApplication
from apps.billing.models import PlacementFee
from apps.colleges.models import College
from apps.companies.models import Company
from apps.faculty.models import FacultyVacancy
from apps.invoices.models import Invoice
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.academic_recruitment.models import ProfessorProfile
from apps.jobs.models import JobPosting

CACHE_TIMEOUT = 900  # 15 minutes


class DashboardSelector:
    def seeker_summary(self, user: ITUser) -> dict:
        cache_key = f"dashboard:seeker:{user.pk}"
        def _get_data():
            profile = JobSeekerProfile.objects.filter(user=user, is_deleted=False).first()
            if not profile:
                return {
                    "has_profile": False,
                    "applications_total": 0,
                    "applications_by_status": {},
                }

            qs = JobApplication.objects.filter(job_seeker=profile, is_deleted=False)
            by_status = dict(
                qs.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            )
            return {
                "has_profile": True,
                "profile_id": str(profile.pk),
                "applications_total": qs.count(),
                "applications_by_status": by_status,
            }
        return cache.get_or_set(cache_key, _get_data, CACHE_TIMEOUT)

    def recruiter_summary(self, user: ITUser) -> dict:
        cache_key = f"dashboard:recruiter:{user.pk}"
        def _get_data():
            profile = RecruiterProfile.objects.filter(user=user, is_deleted=False).first()
            if not profile:
                return {
                    "has_profile": False,
                    "companies": 0,
                    "jobs_total": 0,
                    "jobs_published": 0,
                    "applications_received": 0,
                    "applications_by_status": {},
                }

            company_ids = profile.company_memberships.filter(
                is_active=True, is_deleted=False
            ).values_list("company_id", flat=True)
            jobs = JobPosting.objects.filter(company_id__in=company_ids, is_deleted=False)
            applications = JobApplication.objects.filter(
                job_posting__company_id__in=company_ids, is_deleted=False
            )
            by_status = dict(
                applications.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            )
            return {
                "has_profile": True,
                "profile_id": str(profile.pk),
                "companies": profile.company_memberships.filter(
                    is_active=True, is_deleted=False
                ).count(),
                "jobs_total": jobs.count(),
                "jobs_published": jobs.filter(
                    status=JobPosting.JobStatus.PUBLISHED
                ).count(),
                "applications_received": applications.count(),
                "applications_by_status": by_status,
            }
        return cache.get_or_set(cache_key, _get_data, CACHE_TIMEOUT)

    def professor_summary(self, user: ProfessorUser) -> dict:
        cache_key = f"dashboard:professor:{user.pk}"
        def _get_data():
            profile = ProfessorProfile.objects.filter(user=user, is_deleted=False).first()
            if not profile:
                return {
                    "has_profile": False,
                    "applications_total": 0,
                    "applications_by_status": {},
                }

            qs = FacultyApplication.objects.filter(professor=profile, is_deleted=False)
            by_status = dict(
                qs.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            )
            return {
                "has_profile": True,
                "profile_id": str(profile.pk),
                "applications_total": qs.count(),
                "applications_by_status": by_status,
            }
        return cache.get_or_set(cache_key, _get_data, CACHE_TIMEOUT)

    def college_summary(self, user: CollegeUser) -> dict:
        cache_key = f"dashboard:college:{user.pk}"
        def _get_data():
            memberships = user.college_memberships.filter(is_active=True, is_deleted=False)
            college_ids = memberships.values_list("college_id", flat=True)
            vacancies = FacultyVacancy.objects.filter(
                college_id__in=college_ids, is_deleted=False
            )
            applications = FacultyApplication.objects.filter(
                vacancy__college_id__in=college_ids, is_deleted=False
            )
            by_status = dict(
                applications.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            )
            return {
                "colleges": memberships.count(),
                "vacancies_total": vacancies.count(),
                "vacancies_published": vacancies.filter(
                    status=FacultyVacancy.VacancyStatus.PUBLISHED
                ).count(),
                "applications_received": applications.count(),
                "applications_by_status": by_status,
            }
        return cache.get_or_set(cache_key, _get_data, CACHE_TIMEOUT)

    def admin_summary(self) -> dict:
        cache_key = "dashboard:admin"
        def _get_data():
            return {
                "users": {
                    "it": ITUser.objects.filter(is_deleted=False, is_active=True).count(),
                    "professor": ProfessorUser.objects.filter(
                        is_deleted=False, is_active=True
                    ).count(),
                    "college": CollegeUser.objects.filter(
                        is_deleted=False, is_active=True
                    ).count(),
                    "admin": AdminUser.objects.filter(
                        is_deleted=False, is_active=True
                    ).count(),
                },
                "it": {
                    "companies": Company.objects.filter(is_deleted=False).count(),
                    "jobs_published": JobPosting.objects.filter(
                        is_deleted=False, status=JobPosting.JobStatus.PUBLISHED
                    ).count(),
                    "applications": JobApplication.objects.filter(is_deleted=False).count(),
                },
                "faculty": {
                    "colleges": College.objects.filter(is_deleted=False).count(),
                    "vacancies_published": FacultyVacancy.objects.filter(
                        is_deleted=False, status=FacultyVacancy.VacancyStatus.PUBLISHED
                    ).count(),
                    "applications": FacultyApplication.objects.filter(
                        is_deleted=False
                    ).count(),
                },
                "billing": {
                    "placement_fees": PlacementFee.objects.filter(is_deleted=False).count(),
                    "invoices": Invoice.objects.filter(is_deleted=False).count(),
                },
            }
        return cache.get_or_set(cache_key, _get_data, CACHE_TIMEOUT)
