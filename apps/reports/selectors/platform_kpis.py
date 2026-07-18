from django.db.models import Count, Sum

from apps.applications.models import FacultyApplication, JobApplication
from apps.billing.models import PlacementFee
from apps.faculty.models import FacultyVacancy
from apps.guarantee_claims.models import GuaranteeClaim
from apps.invoices.models import Invoice
from apps.jobs.models import JobPosting


class PlatformKPIsSelector:
    def platform_overview(self) -> dict:
        return {
            "applications": {
                "it_total": JobApplication.objects.filter(is_deleted=False).count(),
                "it_hired": JobApplication.objects.filter(
                    is_deleted=False, status=JobApplication.ApplicationStatus.HIRED
                ).count(),
                "faculty_total": FacultyApplication.objects.filter(
                    is_deleted=False
                ).count(),
                "faculty_joined": FacultyApplication.objects.filter(
                    is_deleted=False, status="joined"
                ).count(),
            },
            "postings": {
                "jobs_published": JobPosting.objects.filter(
                    is_deleted=False, status=JobPosting.JobStatus.PUBLISHED
                ).count(),
                "vacancies_published": FacultyVacancy.objects.filter(
                    is_deleted=False, status=FacultyVacancy.VacancyStatus.PUBLISHED
                ).count(),
            },
            "revenue": {
                "placement_fees_total": PlacementFee.objects.filter(
                    is_deleted=False
                ).count(),
                "fees_amount_sum": PlacementFee.objects.filter(
                    is_deleted=False
                ).aggregate(total=Sum("calculated_amount"))["total"]
                or 0,
                "invoices_issued": Invoice.objects.filter(is_deleted=False)
                .exclude(status__in=("draft", "cancelled"))
                .count(),
                "invoices_paid": Invoice.objects.filter(
                    is_deleted=False, status="paid"
                ).count(),
                "invoices_overdue": Invoice.objects.filter(
                    is_deleted=False, status="overdue"
                ).count(),
                "invoices_refunded": Invoice.objects.filter(
                    is_deleted=False, status="refunded"
                ).count(),
            },
            "claims": {
                "total": GuaranteeClaim.objects.filter(is_deleted=False).count(),
                "open": GuaranteeClaim.objects.filter(is_deleted=False)
                .exclude(status__in=("resolved", "rejected"))
                .count(),
            },
        }

    def it_pipeline(self) -> dict:
        return dict(
            JobApplication.objects.filter(is_deleted=False)
            .values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )

    def faculty_pipeline(self) -> dict:
        return dict(
            FacultyApplication.objects.filter(is_deleted=False)
            .values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
