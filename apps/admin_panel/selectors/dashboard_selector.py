from django.db.models import Count, Sum
from django.utils import timezone
from apps.admin_panel.utils.trend_analyzer import TrendAnalyzer

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models import ProfessorProfile
from apps.applications.constants.enums import JobApplicationStatus
from apps.applications.models import FacultyApplication, JobApplication
from apps.audit.models import AuditEvent
from apps.billing.models import PlacementFee
from apps.colleges.models import College
from apps.companies.models import Company
from apps.faculty.models import FacultyVacancy
from apps.guarantee_claims.constants.enums import ClaimResolution, ClaimStatus
from apps.guarantee_claims.models import GuaranteeClaim
from apps.invoices.constants.enums import InvoiceStatus
from apps.invoices.models import Invoice
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.jobs.models import JobPosting


class DashboardSelector:
    """Enterprise admin dashboard metrics."""

    def summary(self) -> dict:
        it_users = ITUser.objects.filter(is_deleted=False)
        recruiters = RecruiterProfile.objects.filter(is_deleted=False).count()
        job_seekers = JobSeekerProfile.objects.filter(is_deleted=False).count()
        professors = ProfessorProfile.objects.filter(is_deleted=False).count()
        colleges = College.objects.filter(is_deleted=False)
        companies = Company.objects.filter(is_deleted=False)
        jobs = JobPosting.objects.filter(is_deleted=False)
        vacancies = FacultyVacancy.objects.filter(is_deleted=False)
        it_apps = JobApplication.objects.filter(is_deleted=False)
        faculty_apps = FacultyApplication.objects.filter(is_deleted=False)
        invoices = Invoice.objects.filter(is_deleted=False)
        claims = GuaranteeClaim.objects.filter(is_deleted=False)

        successful_placements = (
            it_apps.filter(status=JobApplicationStatus.HIRED).count()
            + faculty_apps.filter(status="joined").count()
        )
        revenue = (
            PlacementFee.objects.filter(is_deleted=False).aggregate(
                total=Sum("calculated_amount")
            )["total"]
            or 0
        )
        paid_revenue = (
            invoices.filter(status=InvoiceStatus.PAID).aggregate(
                total=Sum("amount_paid")
            )["total"]
            or 0
        )

        return {
            "users": {
                "total": (
                    it_users.filter(is_active=True).count()
                    + ProfessorUser.objects.filter(
                        is_deleted=False, is_active=True
                    ).count()
                    + CollegeUser.objects.filter(
                        is_deleted=False, is_active=True
                    ).count()
                    + AdminUser.objects.filter(is_deleted=False, is_active=True).count()
                ),
                "recruiters": recruiters,
                "job_seekers": job_seekers,
                "professors": professors,
                "college_users": CollegeUser.objects.filter(
                    is_deleted=False, is_active=True
                ).count(),
                "admin_users": AdminUser.objects.filter(
                    is_deleted=False, is_active=True
                ).count(),
            },
            "organizations": {
                "companies": companies.count(),
                "colleges": colleges.count(),
            },
            "postings": {
                "active_jobs": jobs.filter(
                    status=JobPosting.JobStatus.PUBLISHED
                ).count(),
                "active_vacancies": vacancies.filter(
                    status=FacultyVacancy.VacancyStatus.PUBLISHED
                ).count(),
            },
            "applications": {
                "job_applications": it_apps.count(),
                "faculty_applications": faculty_apps.count(),
                "successful_placements": successful_placements,
            },
            "billing": {
                "revenue_total": str(revenue),
                "revenue_collected": str(paid_revenue),
                "pending_invoices": invoices.filter(
                    status__in=(
                        InvoiceStatus.ISSUED,
                        InvoiceStatus.PENDING,
                        InvoiceStatus.PARTIALLY_PAID,
                        InvoiceStatus.OVERDUE,
                    )
                ).count(),
                "paid_invoices": invoices.filter(status=InvoiceStatus.PAID).count(),
                "overdue_invoices": invoices.filter(
                    status=InvoiceStatus.OVERDUE
                ).count(),
                "guarantee_claims_open": claims.exclude(
                    status__in=(ClaimStatus.RESOLVED, ClaimStatus.REJECTED)
                ).count(),
            },
        }

    def get_kpis(self, **filters) -> dict:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        domain = filters.get("domain", "all")
        invoices = Invoice.objects.filter(is_deleted=False, status=InvoiceStatus.PAID)
        if domain != "all":
            invoices = invoices.filter(domain=domain)

        # Financials
        total_rev = invoices.aggregate(total=Sum("amount_paid"))["total"] or 0
        month_rev = (
            invoices.filter(paid_at__gte=month_start).aggregate(
                total=Sum("amount_paid")
            )["total"]
            or 0
        )
        today_rev = (
            invoices.filter(paid_at__gte=today_start).aggregate(
                total=Sum("amount_paid")
            )["total"]
            or 0
        )

        out_qs = Invoice.objects.filter(
            is_deleted=False,
            status__in=(
                InvoiceStatus.ISSUED,
                InvoiceStatus.PENDING,
                InvoiceStatus.PARTIALLY_PAID,
                InvoiceStatus.OVERDUE,
            ),
        )
        if domain != "all":
            out_qs = out_qs.filter(domain=domain)
        outstanding_data = out_qs.aggregate(total_amount=Sum("total_amount"), total_paid=Sum("amount_paid"))

        outstanding = (outstanding_data["total_amount"] or 0) - (
            outstanding_data["total_paid"] or 0
        )

        claims = GuaranteeClaim.objects.filter(is_deleted=False)
        # Sum refund amounts from invoices whose status is REFUNDED (set by RefundService)
        refunded_invoice_ids = claims.filter(
            status=ClaimStatus.RESOLVED, resolution=ClaimResolution.REFUND
        ).values_list("invoice_id", flat=True)
        total_refunded = (
            Invoice.objects.filter(
                pk__in=refunded_invoice_ids, is_deleted=False
            ).aggregate(total=Sum("amount_paid"))["total"]
            or 0
        )
        open_claims_count = claims.exclude(
            status__in=(ClaimStatus.RESOLVED, ClaimStatus.REJECTED)
        ).count()
        total_claims_count = claims.count()

        # Organizations & Recruiters
        active_it_recruiters = RecruiterProfile.objects.filter(
            is_deleted=False, user__is_active=True
        ).count()
        active_fac_recruiters = CollegeUser.objects.filter(
            is_deleted=False, is_active=True
        ).count()

        reg_it_seekers = TrendAnalyzer.analyze_queryset_count(
            JobSeekerProfile.objects.filter(is_deleted=False), period="month"
        )
        reg_fac_seekers = TrendAnalyzer.analyze_queryset_count(
            ProfessorProfile.objects.filter(is_deleted=False), period="month"
        )

        institutions = TrendAnalyzer.analyze_queryset_count(
            College.objects.filter(is_deleted=False), period="month"
        )
        companies = TrendAnalyzer.analyze_queryset_count(
            Company.objects.filter(is_deleted=False), period="month"
        )

        # Postings
        pub_jobs = TrendAnalyzer.analyze_queryset_count(
            JobPosting.objects.filter(
                is_deleted=False, status=JobPosting.JobStatus.PUBLISHED
            ),
            date_field="published_at",
            period="month",
        )
        pub_vacs = TrendAnalyzer.analyze_queryset_count(
            FacultyVacancy.objects.filter(
                is_deleted=False, status=FacultyVacancy.VacancyStatus.PUBLISHED
            ),
            date_field="published_at",
            period="month",
        )

        # Applications
        it_apps_today = JobApplication.objects.filter(
            is_deleted=False, created_at__gte=today_start
        ).count()
        fac_apps_today = FacultyApplication.objects.filter(
            is_deleted=False, created_at__gte=today_start
        ).count()

        interviews_it = JobApplication.objects.filter(
            is_deleted=False, status=JobApplicationStatus.INTERVIEW_SCHEDULED
        ).count()
        interviews_fac = FacultyApplication.objects.filter(
            is_deleted=False, status="interview"
        ).count()

        offers_it = JobApplication.objects.filter(
            is_deleted=False, status=JobApplicationStatus.OFFER_RELEASED
        ).count()
        offers_fac = FacultyApplication.objects.filter(
            is_deleted=False, status="offered"
        ).count()

        hires_it = JobApplication.objects.filter(
            is_deleted=False, status=JobApplicationStatus.HIRED
        ).count()
        hires_fac = FacultyApplication.objects.filter(
            is_deleted=False, status="joined"
        ).count()

        return {
            "financials": {
                "total_revenue": total_rev,
                "revenue_this_month": month_rev,
                "revenue_today": today_rev,
                "outstanding_payments": outstanding,
                "total_refunded": total_refunded,
                "open_claims_count": open_claims_count,
                "total_claims_count": total_claims_count,
            },
            "users": {
                "active_it_recruiters": active_it_recruiters,
                "active_faculty_recruiters": active_fac_recruiters,
                "registered_it_seekers": reg_it_seekers,
                "registered_faculty_seekers": reg_fac_seekers,
                "institutions": institutions,
                "companies": companies,
            },
            "postings": {
                "published_jobs": pub_jobs,
                "published_vacancies": pub_vacs,
            },
            "pipeline": {
                "applications_today": (it_apps_today if domain in ("all", "it") else 0) + (fac_apps_today if domain in ("all", "faculty") else 0),
                "interviews_scheduled": (interviews_it if domain in ("all", "it") else 0) + (interviews_fac if domain in ("all", "faculty") else 0),
                "offers_released": (offers_it if domain in ("all", "it") else 0) + (offers_fac if domain in ("all", "faculty") else 0),
                "successful_hires": (hires_it if domain in ("all", "it") else 0) + (hires_fac if domain in ("all", "faculty") else 0),
            },
        }

    def recent_activities(self, *, limit: int = 20) -> list[dict]:
        events = AuditEvent.objects.order_by("-occurred_at")[:limit]
        return [
            {
                "id": str(event.pk),
                "domain": event.domain,
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": str(event.entity_id) if event.entity_id else None,
                "actor_type": event.actor_type,
                "actor_id": str(event.actor_id) if event.actor_id else None,
                "occurred_at": event.occurred_at.isoformat(),
            }
            for event in events
        ]

    def action_center(self) -> dict:
        pending_colleges = College.objects.filter(
            is_deleted=False, is_active=False
        ).order_by("created_at")[:5]
        pending_companies = Company.objects.filter(
            is_deleted=False, is_active=False
        ).order_by("created_at")[:5]
        pending_jobs = JobPosting.objects.filter(
            is_deleted=False, status=JobPosting.JobStatus.DRAFT
        ).order_by("created_at")[:5]  # assuming draft or pending review
        pending_vacancies = FacultyVacancy.objects.filter(
            is_deleted=False, status=FacultyVacancy.VacancyStatus.DRAFT
        ).order_by("created_at")[:5]
        open_claims = (
            GuaranteeClaim.objects.filter(is_deleted=False)
            .exclude(status__in=(ClaimStatus.RESOLVED, ClaimStatus.REJECTED))
            .order_by("created_at")[:5]
        )

        return {
            "pending_colleges": [
                {
                    "id": str(c.pk),
                    "name": c.name,
                    "created_at": c.created_at.isoformat(),
                }
                for c in pending_colleges
            ],
            "pending_companies": [
                {
                    "id": str(c.pk),
                    "name": c.name,
                    "created_at": c.created_at.isoformat(),
                }
                for c in pending_companies
            ],
            "pending_jobs": [
                {
                    "id": str(j.pk),
                    "title": j.title,
                    "company": getattr(j.company, "name", "Unknown"),
                    "created_at": j.created_at.isoformat(),
                }
                for j in pending_jobs
            ],
            "pending_vacancies": [
                {
                    "id": str(v.pk),
                    "title": v.title,
                    "college": getattr(v.college, "name", "Unknown"),
                    "created_at": v.created_at.isoformat(),
                }
                for v in pending_vacancies
            ],
            "open_claims": [
                {
                    "id": str(c.pk),
                    "claim_number": c.claim_number,
                    "claim_type": c.claim_type,
                    "reason": c.reason[:120] if c.reason else "",
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                }
                for c in open_claims
            ],
        }

    def system_health(self) -> dict:
        from django.conf import settings
        from django.db import connection

        checks = {"database": "error", "redis": "error", "celery": "error"}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception:
            pass
        try:
            import redis

            client = redis.from_url(settings.REDIS_URL)
            client.ping()
            checks["redis"] = "ok"
        except Exception:
            pass
        try:
            from config.celery import app

            conn = app.connection()
            conn.ensure_connection(max_retries=1)
            conn.release()
            checks["celery"] = "ok"
        except Exception:
            pass
        status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
        return {
            "status": status,
            "checks": checks,
            "checked_at": timezone.now().isoformat(),
        }
