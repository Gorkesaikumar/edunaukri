from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
from django.db import models

from apps.applications.models import FacultyApplication, JobApplication
from apps.audit.models import AuditEvent
from apps.billing.models import PlacementFee
from apps.colleges.models import College
from apps.companies.models import Company, CompanyMember
from apps.faculty.models import FacultyVacancy
from apps.invoices.models import Invoice
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.models import JobPosting


import hashlib
import json
from functools import wraps
from django.core.cache import cache

def cache_analytics(timeout=900):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            key_string = f"analytics:{func.__name__}:" + json.dumps(kwargs, sort_keys=True)
            cache_key = hashlib.md5(key_string.encode("utf-8")).hexdigest()
            return cache.get_or_set(cache_key, lambda: func(self, *args, **kwargs), timeout)
        return wrapper
    return decorator

class AnalyticsSelector:
    """Platform analytics for the admin panel."""

    @cache_analytics(900)
    def monthly_placements(self, *, months: int = 12) -> list[dict]:
        since = timezone.now() - timezone.timedelta(days=months * 31)
        it_hired = (
            JobApplication.objects.filter(
                is_deleted=False, hired_at__gte=since, hired_at__isnull=False
            )
            .annotate(month=TruncMonth("hired_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        faculty_joined = (
            FacultyApplication.objects.filter(
                is_deleted=False, joined_at__gte=since, joined_at__isnull=False
            )
            .annotate(month=TruncMonth("joined_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        merged: dict[str, dict] = {}
        for row in it_hired:
            key = row["month"].strftime("%Y-%m") if row["month"] else "unknown"
            merged.setdefault(
                key, {"month": key, "it_placements": 0, "faculty_placements": 0}
            )
            merged[key]["it_placements"] = row["count"]
        for row in faculty_joined:
            key = row["month"].strftime("%Y-%m") if row["month"] else "unknown"
            merged.setdefault(
                key, {"month": key, "it_placements": 0, "faculty_placements": 0}
            )
            merged[key]["faculty_placements"] = row["count"]
        return sorted(merged.values(), key=lambda r: r["month"])

    @cache_analytics(900)
    def application_trends(self) -> dict:
        it = dict(
            JobApplication.objects.filter(is_deleted=False)
            .values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        faculty = dict(
            FacultyApplication.objects.filter(is_deleted=False)
            .values("status")
            .annotate(count=Count("id"))
            .values_list("status", "count")
        )
        return {"it": it, "faculty": faculty}

    @cache_analytics(900)
    def revenue_trends(self, *, months: int = 12) -> list[dict]:
        since = timezone.now() - timezone.timedelta(days=months * 31)
        rows = (
            Invoice.objects.filter(
                is_deleted=False, paid_at__gte=since, paid_at__isnull=False
            )
            .annotate(month=TruncMonth("paid_at"))
            .values("month")
            .annotate(total=Sum("amount_paid"), count=Count("id"))
            .order_by("month")
        )
        return [
            {
                "month": row["month"].strftime("%Y-%m") if row["month"] else "unknown",
                "total_collected": str(row["total"] or 0),
                "invoice_count": row["count"],
            }
            for row in rows
        ]

    @cache_analytics(900)
    def top_recruiters(self, *, limit: int = 10) -> list[dict]:
        rows = (
            CompanyMember.objects.filter(is_active=True, is_deleted=False)
            .values("recruiter_id")
            .annotate(companies=Count("company_id", distinct=True))
            .order_by("-companies")[:limit]
        )
        recruiter_ids = [row["recruiter_id"] for row in rows if row["recruiter_id"]]
        recruiters = {
            recruiter.pk: recruiter
            for recruiter in RecruiterProfile.objects.filter(pk__in=recruiter_ids)
        }
        result = []
        for row in rows:
            recruiter = recruiters.get(row["recruiter_id"])
            if recruiter:
                result.append(
                    {
                        "recruiter_id": str(recruiter.pk),
                        "name": recruiter.full_name,
                        "companies": row["companies"],
                    }
                )
        return result

    @cache_analytics(900)
    def top_companies(self, *, limit: int = 10) -> list[dict]:
        rows = (
            JobPosting.objects.filter(is_deleted=False)
            .values("company_id", "company_name_snapshot")
            .annotate(jobs=Count("id"))
            .order_by("-jobs")[:limit]
        )
        return [
            {
                "company_id": str(row["company_id"]),
                "name": row["company_name_snapshot"],
                "jobs": row["jobs"],
            }
            for row in rows
        ]

    @cache_analytics(900)
    def top_colleges(self, *, limit: int = 10) -> list[dict]:
        rows = (
            FacultyVacancy.objects.filter(is_deleted=False)
            .values("college_id", "college_name_snapshot")
            .annotate(vacancies=Count("id"))
            .order_by("-vacancies")[:limit]
        )
        return [
            {
                "college_id": str(row["college_id"]),
                "name": row["college_name_snapshot"],
                "vacancies": row["vacancies"],
            }
            for row in rows
        ]

    @cache_analytics(900)
    def most_applied_jobs(self, *, limit: int = 10) -> list[dict]:
        rows = (
            JobPosting.objects.filter(is_deleted=False)
            .order_by("-application_count")[:limit]
            .values("id", "title", "company_name_snapshot", "application_count")
        )
        return [
            {
                "job_id": str(row["id"]),
                "title": row["title"],
                "company": row["company_name_snapshot"],
                "applications": row["application_count"],
            }
            for row in rows
        ]

    @cache_analytics(900)
    def most_applied_vacancies(self, *, limit: int = 10) -> list[dict]:
        rows = (
            FacultyVacancy.objects.filter(is_deleted=False)
            .order_by("-application_count")[:limit]
            .values("id", "title", "college_name_snapshot", "application_count")
        )
        return [
            {
                "vacancy_id": str(row["id"]),
                "title": row["title"],
                "college": row["college_name_snapshot"],
                "applications": row["application_count"],
            }
            for row in rows
        ]

    @cache_analytics(900)
    def active_users_trend(self, *, days: int = 30) -> list[dict]:
        since = timezone.now() - timezone.timedelta(days=days)
        rows = (
            AuditEvent.objects.filter(
                event_type__icontains="login", occurred_at__gte=since
            )
            .annotate(day=TruncDay("occurred_at"))
            .values("day")
            .annotate(count=Count("actor_id", distinct=True))
            .order_by("day")
        )
        return [
            {
                "date": row["day"].strftime("%Y-%m-%d") if row["day"] else "unknown",
                "active_users": row["count"],
            }
            for row in rows
        ]

    @cache_analytics(900)
    def overview(self) -> dict:
        return {
            "monthly_placements": self.monthly_placements(),
            "application_trends": self.application_trends(),
            "revenue_trends": self.revenue_trends(),
            "top_recruiters": self.top_recruiters(),
            "top_companies": self.top_companies(),
            "top_colleges": self.top_colleges(),
            "most_applied_jobs": self.most_applied_jobs(),
            "most_applied_vacancies": self.most_applied_vacancies(),
            "active_users_trend": self.active_users_trend(),
        }

    def _apply_filters(self, qs, filters, date_field="created_at"):
        domain = filters.get("domain")
        if domain and domain != "all":
            qs = qs.filter(domain=domain)
            
        org_id = filters.get("org_id")
        if org_id:
            qs = qs.filter(bill_to_entity_id=org_id)
            
        invoice_status = filters.get("invoice_status")
        if invoice_status:
            qs = qs.filter(status=invoice_status)
            
        payment_status = filters.get("payment_status")
        if payment_status:
            if payment_status == "paid":
                qs = qs.filter(amount_paid__gte=models.F('total_amount'))
            elif payment_status == "partial":
                qs = qs.filter(amount_paid__gt=0, amount_paid__lt=models.F('total_amount'))
            elif payment_status == "unpaid":
                qs = qs.filter(amount_paid=0)

        # Basic global search
        search = filters.get("search")
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(candidate_name__icontains=search) |
                Q(bill_to_name_snapshot__icontains=search) |
                Q(invoice_number__icontains=search)
            )
            
        # Optional: date_range (simple support)
        date_range = filters.get("date_range")
        if date_range:
            from datetime import timedelta
            now = timezone.now()
            if date_range == "7d":
                qs = qs.filter(**{f"{date_field}__gte": now - timedelta(days=7)})
            elif date_range == "30d":
                qs = qs.filter(**{f"{date_field}__gte": now - timedelta(days=30)})
            elif date_range == "90d":
                qs = qs.filter(**{f"{date_field}__gte": now - timedelta(days=90)})
                
        return qs

    @cache_analytics(900)
    def placement_analytics(self, **filters) -> dict:
        """Returns placement analytics and totals."""
        qs = Invoice.objects.filter(is_deleted=False)
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        
        # Calculate summaries
        totals = qs.values('domain').annotate(count=Count('id'))
        total_it = sum(t['count'] for t in totals if t['domain'] == 'it')
        total_faculty = sum(t['count'] for t in totals if t['domain'] == 'faculty')
        
        placements = []
        for inv in qs.order_by('-issued_at')[:100]:
            placements.append({
                "candidate_name": inv.candidate_name or "Unknown",
                "domain": inv.domain,
                "recruiter": inv.bill_to_name_snapshot,
                "job_title": inv.candidate_job_title or "-",
                "salary": float(inv.candidate_annual_ctc or 0),
                "joining_date": inv.issued_at.date().isoformat() if inv.issued_at else "-",
                "status": "Placed",
                "invoice_status": inv.status,
                "invoice_number": inv.invoice_number,
            })
            
        return {
            "total_it": total_it,
            "total_faculty": total_faculty,
            "total_placements": total_it + total_faculty,
            "results": placements,
        }

    @cache_analytics(900)
    def revenue_analytics(self, **filters) -> list[dict]:
        """Aggregate revenue per organization."""
        qs = Invoice.objects.filter(is_deleted=False)
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        
        orgs = qs.values(
            'bill_to_entity_id', 'bill_to_name_snapshot', 'domain'
        ).annotate(
            candidates_hired=Count('id'),
            total_fee=Sum('subtotal'),
            total_gst=Sum('tax_amount'),
            total_invoice=Sum('total_amount'),
            total_paid=Sum('amount_paid'),
            last_payment=models.Max('paid_at')
        ).order_by('-total_invoice')[:100]
        
        results = []
        for org in orgs:
            results.append({
                "organization_name": org['bill_to_name_snapshot'],
                "domain": org['domain'],
                "candidates_hired": org['candidates_hired'],
                "total_fee": float(org['total_fee'] or 0),
                "total_gst": float(org['total_gst'] or 0),
                "total_invoice": float(org['total_invoice'] or 0),
                "total_paid": float(org['total_paid'] or 0),
                "pending_amount": float((org['total_invoice'] or 0) - (org['total_paid'] or 0)),
                "last_payment_date": org['last_payment'].date().isoformat() if org['last_payment'] else "-",
                "invoice_status": "Paid" if (org['total_invoice'] or 0) <= (org['total_paid'] or 0) else "Pending",
            })
        return results

    @cache_analytics(900)
    def top_revenue_institutions(self, **filters) -> list[dict]:
        """Top institutions by revenue."""
        all_revenue = self.revenue_analytics(**filters)
        all_revenue.sort(key=lambda x: x['total_invoice'], reverse=True)
        
        results = []
        for idx, org in enumerate(all_revenue[:10]):
            results.append({
                "rank": idx + 1,
                "organization_name": org['organization_name'],
                "domain": org['domain'],
                "candidates_hired": org['candidates_hired'],
                "total_revenue": org['total_invoice'],
                "total_paid": org['total_paid'],
                "outstanding_balance": org['pending_amount'],
            })
        return results

    @cache_analytics(900)
    def recent_placements(self, **filters) -> list[dict]:
        """Recent successful placements."""
        qs = Invoice.objects.filter(is_deleted=False)
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        
        placements = []
        for inv in qs.order_by('-issued_at')[:15]:
            placements.append({
                "candidate_name": inv.candidate_name or "Unknown",
                "recruiter": inv.bill_to_name_snapshot,
                "domain": inv.domain,
                "designation": inv.candidate_job_title or "-",
                "salary": float(inv.candidate_annual_ctc or 0),
                "joined_on": inv.issued_at.date().isoformat() if inv.issued_at else "-",
                "invoice_generated": inv.created_at.date().isoformat(),
                "payment_status": "Paid" if inv.amount_paid >= inv.total_amount else "Pending",
            })
        return placements

    @cache_analytics(900)
    def bi_revenue_growth(self, **filters) -> list[dict]:
        qs = Invoice.objects.filter(is_deleted=False, status='paid')
        qs = self._apply_filters(qs, filters, date_field="paid_at")
        
        # Determine grouping based on date_range
        date_range = filters.get("date_range", "30d")
        if date_range in ("today", "7d", "30d"):
            grouping = TruncDay("paid_at")
            fmt = "%Y-%m-%d"
        else:
            grouping = TruncMonth("paid_at")
            fmt = "%Y-%m"

        rows = (
            qs.annotate(period=grouping)
            .values("period")
            .annotate(total=Sum("amount_paid"))
            .order_by("period")
        )
        return [
            {
                "date": row["period"].strftime(fmt) if row["period"] else "unknown",
                "revenue": float(row["total"] or 0),
            }
            for row in rows
        ]

    @cache_analytics(900)
    def bi_revenue_by_org(self, **filters) -> list[dict]:
        qs = Invoice.objects.filter(is_deleted=False)
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        
        orgs = (
            qs.values('bill_to_name_snapshot', 'domain')
            .annotate(total_revenue=Sum('amount_paid'), placements=Count('id'))
            .order_by('-total_revenue')[:10]
        )
        total_all_rev = float(sum(org['total_revenue'] or 0 for org in orgs))
        
        results = []
        for org in orgs:
            rev = float(org['total_revenue'] or 0)
            results.append({
                "name": org['bill_to_name_snapshot'] or "Unknown",
                "domain": org['domain'],
                "revenue": rev,
                "placements": org['placements'],
                "contribution_pct": round((rev / total_all_rev * 100), 1) if total_all_rev else 0,
            })
        return results

    @cache_analytics(900)
    def bi_placement_analytics(self, **filters) -> dict:
        # We need counts for Applications, Shortlisted, Interviewed, Selected, Joined
        # We will use simple counts
        it_qs = JobApplication.objects.filter(is_deleted=False)
        it_qs = self._apply_filters(it_qs, filters, date_field="created_at")
        
        fac_qs = FacultyApplication.objects.filter(is_deleted=False)
        fac_qs = self._apply_filters(fac_qs, filters, date_field="created_at")
        
        it_counts = dict(it_qs.values("status").annotate(c=Count("id")).values_list("status", "c"))
        fac_counts = dict(fac_qs.values("status").annotate(c=Count("id")).values_list("status", "c"))
        
        return {
            "it": {
                "applications": sum(it_counts.values()),
                "shortlisted": it_counts.get("shortlisted", 0),
                "interviewed": it_counts.get("interview_scheduled", 0),
                "selected": it_counts.get("offer_released", 0) + it_counts.get("hired", 0),
                "joined": it_counts.get("hired", 0),
            },
            "faculty": {
                "applications": sum(fac_counts.values()),
                "shortlisted": fac_counts.get("shortlisted", 0),
                "interviewed": fac_counts.get("interview", 0),
                "selected": fac_counts.get("offered", 0) + fac_counts.get("joined", 0),
                "joined": fac_counts.get("joined", 0),
            }
        }

    @cache_analytics(900)
    def bi_monthly_placement_trend(self, **filters) -> list[dict]:
        it_qs = JobApplication.objects.filter(is_deleted=False, status='hired', hired_at__isnull=False)
        it_qs = self._apply_filters(it_qs, filters, date_field="hired_at")
        
        fac_qs = FacultyApplication.objects.filter(is_deleted=False, status='joined', joined_at__isnull=False)
        fac_qs = self._apply_filters(fac_qs, filters, date_field="joined_at")
        
        grouping = TruncMonth("hired_at")
        fac_grouping = TruncMonth("joined_at")
        
        it_rows = it_qs.annotate(month=grouping).values("month").annotate(c=Count("id")).order_by("month")
        fac_rows = fac_qs.annotate(month=fac_grouping).values("month").annotate(c=Count("id")).order_by("month")
        
        merged = {}
        for r in it_rows:
            key = r["month"].strftime("%Y-%m") if r["month"] else "unknown"
            merged.setdefault(key, {"month": key, "it": 0, "faculty": 0})["it"] = r["c"]
        for r in fac_rows:
            key = r["month"].strftime("%Y-%m") if r["month"] else "unknown"
            merged.setdefault(key, {"month": key, "it": 0, "faculty": 0})["faculty"] = r["c"]
            
        return sorted(merged.values(), key=lambda x: x["month"])

    @cache_analytics(900)
    def bi_revenue_vs_placements(self, **filters) -> list[dict]:
        rev_data = self.bi_revenue_growth(**filters)
        placements_data = self.bi_monthly_placement_trend(**filters) # this is grouped by month
        
        # Merge them based on date/month keys
        # If rev_data is daily, this might be tricky, so let's force month for this chart
        qs = Invoice.objects.filter(is_deleted=False, status='paid')
        qs = self._apply_filters(qs, filters, date_field="paid_at")
        rev_rows = qs.annotate(month=TruncMonth("paid_at")).values("month").annotate(total=Sum("amount_paid")).order_by("month")
        
        merged = {}
        for r in rev_rows:
            key = r["month"].strftime("%Y-%m") if r["month"] else "unknown"
            merged.setdefault(key, {"period": key, "revenue": 0, "placements": 0})["revenue"] = float(r["total"] or 0)
            
        for r in placements_data:
            key = r["month"]
            merged.setdefault(key, {"period": key, "revenue": 0, "placements": 0})["placements"] += (r["it"] + r["faculty"])
            
        return sorted(merged.values(), key=lambda x: x["period"])

    @cache_analytics(900)
    def bi_top_recruiters(self, **filters) -> list[dict]:
        qs = Invoice.objects.filter(is_deleted=False, domain='it')
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        
        orgs = qs.values('bill_to_name_snapshot').annotate(
            placements=Count('id'),
            revenue=Sum('total_amount'),
            paid=Sum('amount_paid')
        ).order_by('-revenue')[:10]
        
        return [{
            "name": o['bill_to_name_snapshot'] or "Unknown",
            "domain": "IT",
            "placements": o['placements'],
            "revenue": float(o['revenue'] or 0),
            "paid": float(o['paid'] or 0),
            "outstanding": float((o['revenue'] or 0) - (o['paid'] or 0))
        } for o in orgs]

    @cache_analytics(900)
    def bi_top_institutions(self, **filters) -> list[dict]:
        qs = Invoice.objects.filter(is_deleted=False, domain='faculty')
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        
        orgs = qs.values('bill_to_name_snapshot').annotate(
            placements=Count('id'),
            revenue=Sum('total_amount'),
            paid=Sum('amount_paid')
        ).order_by('-revenue')[:10]
        
        return [{
            "name": o['bill_to_name_snapshot'] or "Unknown",
            "domain": "Faculty",
            "placements": o['placements'],
            "revenue": float(o['revenue'] or 0),
            "paid": float(o['paid'] or 0),
            "outstanding": float((o['revenue'] or 0) - (o['paid'] or 0))
        } for o in orgs]

    @cache_analytics(900)
    def bi_recent_placements(self, **filters) -> list[dict]:
        qs = Invoice.objects.filter(is_deleted=False)
        qs = self._apply_filters(qs, filters, date_field="issued_at")
        return [{
            "candidate_name": inv.candidate_name or "Unknown",
            "recruiter": inv.bill_to_name_snapshot or "Unknown",
            "job_title": inv.candidate_job_title or "-",
            "domain": inv.domain,
            "joining_date": inv.issued_at.date().isoformat() if inv.issued_at else "-",
            "invoice_generated": inv.created_at.date().isoformat(),
            "payment_status": "Paid" if inv.amount_paid >= inv.total_amount else "Pending"
        } for inv in qs.order_by('-issued_at')[:10]]

    @cache_analytics(900)
    def bi_dashboard_overview(self, **filters) -> dict:
        return {
            "revenue_growth": self.bi_revenue_growth(**filters),
            "revenue_by_org": self.bi_revenue_by_org(**filters),
            "placement_analytics": self.bi_placement_analytics(**filters),
            "monthly_placement_trend": self.bi_monthly_placement_trend(**filters),
            "revenue_vs_placements": self.bi_revenue_vs_placements(**filters),
            "top_recruiters": self.bi_top_recruiters(**filters),
            "top_institutions": self.bi_top_institutions(**filters),
            "recent_placements": self.bi_recent_placements(**filters),
        }

    @cache_analytics(900)
    def enterprise_analytics_overview(self, **filters) -> dict:
        return {
            "placement_analytics": self.placement_analytics(**filters),
            "revenue_analytics": self.revenue_analytics(**filters),
            "top_revenue_institutions": self.top_revenue_institutions(**filters),
            "recent_placements": self.recent_placements(**filters),
        }
