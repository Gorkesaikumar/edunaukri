from django.db.models import Count, Sum

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.applications.models import FacultyApplication, JobApplication
from apps.billing.models import FeeSchedule, PlacementFee
from apps.colleges.models import College
from apps.companies.models import Company
from apps.guarantee_claims.models import GuaranteeClaim
from apps.invoices.models import Invoice
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.academic_recruitment.models import ProfessorProfile
from apps.reports.selectors.platform_kpis import PlatformKPIsSelector


class ReportSelector:
    """Aggregated report datasets for admin exports."""

    def __init__(self):
        self.kpis = PlatformKPIsSelector()

    def user_report(self) -> dict:
        return {
            "it_users": ITUser.objects.filter(is_deleted=False).count(),
            "active_it_users": ITUser.objects.filter(
                is_deleted=False, is_active=True
            ).count(),
            "recruiters": RecruiterProfile.objects.filter(is_deleted=False).count(),
            "job_seekers": JobSeekerProfile.objects.filter(is_deleted=False).count(),
            "professors": ProfessorProfile.objects.filter(is_deleted=False).count(),
            "professor_users": ProfessorUser.objects.filter(is_deleted=False).count(),
            "college_users": CollegeUser.objects.filter(is_deleted=False).count(),
            "admin_users": AdminUser.objects.filter(is_deleted=False).count(),
        }

    def placement_report(self) -> dict:
        kpis = self.kpis.platform_overview()
        return {
            "applications": kpis["applications"],
            "postings": kpis["postings"],
        }

    def company_report(self) -> dict:
        companies = Company.objects.filter(is_deleted=False)
        return {
            "total": companies.count(),
            "active": companies.filter(is_active=True).count(),
            "by_verification_status": dict(
                companies.values("verification_status")
                .annotate(count=Count("id"))
                .values_list("verification_status", "count")
            ),
        }

    def college_report(self) -> dict:
        colleges = College.objects.filter(is_deleted=False)
        return {
            "total": colleges.count(),
            "active": colleges.filter(is_active=True).count(),
            "by_verification_status": dict(
                colleges.values("verification_status")
                .annotate(count=Count("id"))
                .values_list("verification_status", "count")
            ),
        }

    def application_report(self) -> dict:
        return {
            "it_pipeline": self.kpis.it_pipeline(),
            "faculty_pipeline": self.kpis.faculty_pipeline(),
        }

    def invoice_report(self) -> dict:
        invoices = Invoice.objects.filter(is_deleted=False)
        return {
            "total": invoices.count(),
            "by_status": dict(
                invoices.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "total_invoiced": str(
                invoices.aggregate(total=Sum("total_amount"))["total"] or 0
            ),
            "total_collected": str(
                invoices.aggregate(total=Sum("amount_paid"))["total"] or 0
            ),
        }

    def revenue_report(self) -> dict:
        fees = PlacementFee.objects.filter(is_deleted=False)
        return {
            "placement_fees": fees.count(),
            "total_fees": str(
                fees.aggregate(total=Sum("calculated_amount"))["total"] or 0
            ),
            "fee_schedules_active": FeeSchedule.objects.filter(
                is_deleted=False, is_active=True
            ).count(),
            **self.kpis.platform_overview()["revenue"],
        }

    def guarantee_report(self) -> dict:
        claims = GuaranteeClaim.objects.filter(is_deleted=False)
        return {
            "total": claims.count(),
            "by_status": dict(
                claims.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            **self.kpis.platform_overview()["claims"],
        }

    def get_report(self, report_type: str) -> dict:
        mapping = {
            "users": self.user_report,
            "placements": self.placement_report,
            "companies": self.company_report,
            "colleges": self.college_report,
            "applications": self.application_report,
            "invoices": self.invoice_report,
            "revenue": self.revenue_report,
            "guarantees": self.guarantee_report,
            "platform": self.kpis.platform_overview,
        }
        builder = mapping.get(report_type)
        if not builder:
            return {}
        return builder()
