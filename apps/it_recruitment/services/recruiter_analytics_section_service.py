"""Enterprise recruitment analytics for dashboard and reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from apps.applications.constants.enums import ApplicationSource, JobApplicationStatus
from apps.applications.constants.interview_enums import InterviewStatus
from apps.applications.models import JobApplication
from apps.applications.models.interview import JobApplicationInterview
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.jobs.constants.enums import JobStatus
from apps.jobs.models import JobPosting
from apps.jobs.selectors.job_selector import JobPostingSelector

FUNNEL_DEFINITION = (
    ("applications", "Applications", "all"),
    ("screening", "Screening", "screening"),
    ("shortlisted", "Shortlisted", "shortlisted"),
    ("interview_scheduled", "Interview Scheduled", "interview_scheduled"),
    ("interview_completed", "Interview Completed", "interview_completed"),
    ("selected", "Selected", "selected"),
    ("offer_sent", "Offer Sent", "offer_sent"),
    ("offer_accepted", "Offer Accepted", "offer_accepted"),
    ("hired", "Hired", "hired"),
)

_STATUS_GROUPS = {
    "all": None,
    "screening": (
        JobApplicationStatus.APPLIED,
        JobApplicationStatus.UNDER_REVIEW,
        JobApplicationStatus.SHORTLISTED,
        JobApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    ),
    "shortlisted": (
        JobApplicationStatus.SHORTLISTED,
        JobApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    ),
    "interview_scheduled": (
        JobApplicationStatus.INTERVIEW_SCHEDULED,
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    ),
    "interview_completed": (
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    ),
    "selected": (
        JobApplicationStatus.INTERVIEW_COMPLETED,
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    ),
    "offer_sent": (
        JobApplicationStatus.OFFER_RELEASED,
        JobApplicationStatus.OFFER_ACCEPTED,
        JobApplicationStatus.HIRED,
    ),
    "offer_accepted": (JobApplicationStatus.OFFER_ACCEPTED, JobApplicationStatus.HIRED),
    "hired": (JobApplicationStatus.HIRED,),
}

SOURCE_LABELS = {
    ApplicationSource.DIRECT: "Direct Applications",
    ApplicationSource.REFERRAL: "Referrals",
    ApplicationSource.JOB_BOARD: "Job Boards",
    ApplicationSource.INTERNAL: "EduNaukri Portal",
    ApplicationSource.OTHER: "Other Sources",
    "": "EduNaukri Portal",
}


@dataclass
class AnalyticsPeriod:
    key: str
    label: str
    start: date
    end: date

    @classmethod
    def from_request(cls, request) -> AnalyticsPeriod:
        key = (
            request.GET.get("analytics_period") or request.GET.get("period") or "7d"
        ).strip()
        custom_from = (request.GET.get("date_from") or "").strip()
        custom_to = (request.GET.get("date_to") or "").strip()
        now = timezone.localtime()
        today = now.date()

        if key == "custom" and custom_from and custom_to:
            return cls(
                "custom",
                "Custom Range",
                date.fromisoformat(custom_from),
                date.fromisoformat(custom_to),
            )
        if key == "today":
            return cls("today", "Today", today, today)
        if key == "30d":
            return cls("30d", "Last 30 Days", today - timedelta(days=29), today)
        if key == "90d":
            return cls("90d", "Last 90 Days", today - timedelta(days=89), today)
        if key == "month":
            start = today.replace(day=1)
            return cls("month", "This Month", start, today)
        if key == "quarter":
            q_start_month = ((today.month - 1) // 3) * 3 + 1
            start = today.replace(month=q_start_month, day=1)
            return cls("quarter", "This Quarter", start, today)
        if key == "year":
            start = today.replace(month=1, day=1)
            return cls("year", "This Year", start, today)
        return cls("7d", "Last 7 Days", today - timedelta(days=6), today)


class ChartDataService(BaseService):
    def application_trend(self, apps_qs: QuerySet, period: AnalyticsPeriod) -> dict:
        points = []
        cursor = period.start
        total = 0
        max_val = 0
        while cursor <= period.end:
            count = apps_qs.filter(applied_at__date=cursor).count()
            total += count
            max_val = max(max_val, count)
            points.append(
                {
                    "date": cursor.isoformat(),
                    "label": cursor.strftime("%a")
                    if (period.end - period.start).days <= 13
                    else cursor.strftime("%b %d"),
                    "value": count,
                }
            )
            cursor += timedelta(days=1)
        if max_val:
            for p in points:
                p["bar_pct"] = max(4, round((p["value"] / max_val) * 100))
        else:
            for p in points:
                p["bar_pct"] = 4
        return {"points": points, "total": total, "max": max_val}


class FunnelAnalyticsService(BaseService):
    def build(self, apps_qs: QuerySet) -> list[dict]:
        base_count = apps_qs.count()
        stages = []
        prev_value = base_count or 1
        tones = (
            "primary",
            "secondary",
            "tertiary",
            "primary",
            "secondary",
            "tertiary",
            "primary",
            "secondary",
            "success",
        )

        for idx, (key, label, group_key) in enumerate(FUNNEL_DEFINITION):
            if group_key == "all":
                value = base_count
            else:
                statuses = _STATUS_GROUPS[group_key]
                value = apps_qs.filter(status__in=statuses).count()
            pct = round((value / base_count) * 100) if base_count else 0
            drop_off = (
                round(((prev_value - value) / prev_value) * 100)
                if prev_value and idx > 0
                else 0
            )
            if idx == 0:
                drop_off = 0
            stages.append(
                {
                    "key": key,
                    "label": label,
                    "value": value,
                    "pct": pct,
                    "drop_off": max(0, drop_off),
                    "tone": tones[idx % len(tones)],
                    "bar_pct": max(4, round((value / base_count) * 100))
                    if base_count
                    else 0,
                }
            )
            if value > 0:
                prev_value = value
        return stages


class HiringMetricsService(BaseService):
    def build(
        self, apps_qs: QuerySet, jobs_qs: QuerySet, profile: RecruiterProfile
    ) -> list[dict]:
        total = apps_qs.count() or 1
        hired = apps_qs.filter(status=JobApplicationStatus.HIRED)
        hired_count = hired.count()

        avg_days = None
        if hired.filter(hired_at__isnull=False).exists():
            total_days = 0
            n = 0
            for app in hired.filter(hired_at__isnull=False)[:100]:
                if app.hired_at and app.applied_at:
                    total_days += max(0, (app.hired_at - app.applied_at).days)
                    n += 1
            if n:
                avg_days = round(total_days / n)

        interviewed = apps_qs.filter(
            status__in=(
                JobApplicationStatus.INTERVIEW_COMPLETED,
                JobApplicationStatus.OFFER_RELEASED,
                JobApplicationStatus.OFFER_ACCEPTED,
                JobApplicationStatus.HIRED,
            )
        ).count()
        scheduled = apps_qs.filter(
            status=JobApplicationStatus.INTERVIEW_SCHEDULED
        ).count()
        interview_total = interviewed + scheduled

        offers = apps_qs.filter(status=JobApplicationStatus.OFFER_RELEASED).count()
        accepted = apps_qs.filter(status=JobApplicationStatus.OFFER_ACCEPTED).count()

        published = jobs_qs.filter(status=JobStatus.PUBLISHED).count()
        closed = jobs_qs.filter(status=JobStatus.CLOSED).count()
        filled = hired_count
        job_fill_rate = round((filled / published) * 100) if published else 0

        reviewed = apps_qs.exclude(status=JobApplicationStatus.APPLIED).count()
        response_rate = round((reviewed / total) * 100) if total else 0

        productivity = min(
            100,
            round((hired_count * 10 + reviewed * 2 + scheduled) / max(total / 10, 1)),
        )

        return [
            {
                "key": "time_to_hire",
                "label": "Avg. Time to Hire",
                "value": str(avg_days) if avg_days is not None else "—",
                "unit": "days" if avg_days is not None else "",
                "icon": "schedule",
            },
            {
                "key": "interview_success",
                "label": "Interview Success",
                "value": str(
                    round((interviewed / interview_total) * 100)
                    if interview_total
                    else 0
                ),
                "unit": "%",
                "icon": "verified",
            },
            {
                "key": "offer_acceptance",
                "label": "Offer Acceptance",
                "value": str(round((accepted / offers) * 100) if offers else 0),
                "unit": "%",
                "icon": "handshake",
            },
            {
                "key": "conversion_rate",
                "label": "Conversion Rate",
                "value": str(round((hired_count / total) * 100) if total else 0),
                "unit": "%",
                "icon": "trending_up",
            },
            {
                "key": "app_to_hire",
                "label": "Application-to-Hire",
                "value": f"1:{round(total / hired_count)}" if hired_count else "—",
                "unit": "",
                "icon": "filter_alt",
            },
            {
                "key": "response_time",
                "label": "Response Rate",
                "value": str(response_rate),
                "unit": "%",
                "icon": "speed",
            },
            {
                "key": "job_fill_rate",
                "label": "Job Fill Rate",
                "value": str(job_fill_rate),
                "unit": "%",
                "icon": "work_history",
            },
            {
                "key": "productivity",
                "label": "Recruiter Score",
                "value": str(productivity),
                "unit": "/100",
                "icon": "leaderboard",
            },
        ]


class DepartmentAnalyticsService(BaseService):
    def build(self, apps_qs: QuerySet, jobs_qs: QuerySet) -> list[dict]:
        app_rows = (
            apps_qs.values("job_posting__department")
            .annotate(
                applicants=Count("id"),
                hired=Count("id", filter=Q(status=JobApplicationStatus.HIRED)),
            )
            .order_by("-applicants")[:8]
        )
        job_rows = {
            (r["department"] or "General"): r["c"]
            for r in jobs_qs.values("department").annotate(c=Count("id"))
        }
        max_applicants = max((r["applicants"] for r in app_rows), default=0) or 1
        items = []
        for row in app_rows:
            dept = row["job_posting__department"] or "General"
            items.append(
                {
                    "label": dept,
                    "jobs": job_rows.get(dept, 0),
                    "applicants": row["applicants"],
                    "hired": row["hired"],
                    "bar_pct": round((row["applicants"] / max_applicants) * 100),
                }
            )
        if not items:
            for dept, job_count in list(job_rows.items())[:5]:
                items.append(
                    {
                        "label": dept,
                        "jobs": job_count,
                        "applicants": 0,
                        "hired": 0,
                        "bar_pct": 0,
                    }
                )
        return items


class RecruiterAnalyticsSectionService(BaseService):
    """Orchestrates dashboard analytics widgets with period filtering."""

    PERIOD_OPTIONS = (
        {"key": "today", "label": "Today"},
        {"key": "7d", "label": "Last 7 Days"},
        {"key": "30d", "label": "Last 30 Days"},
        {"key": "90d", "label": "Last 90 Days"},
        {"key": "month", "label": "This Month"},
        {"key": "quarter", "label": "This Quarter"},
        {"key": "year", "label": "This Year"},
    )

    def apps_for_period(
        self, profile: RecruiterProfile, period: AnalyticsPeriod
    ) -> QuerySet:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        qs = JobApplication.objects.filter(
            job_posting__company_id__in=company_ids,
            is_deleted=False,
            applied_at__date__gte=period.start,
            applied_at__date__lte=period.end,
        ).select_related("job_posting")
        return qs

    def all_apps(self, profile: RecruiterProfile) -> QuerySet:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        return JobApplication.objects.filter(
            job_posting__company_id__in=company_ids,
            is_deleted=False,
        ).select_related("job_posting")

    def jobs_qs(self, profile: RecruiterProfile) -> QuerySet:
        return JobPostingSelector().for_recruiter(profile).select_related("company")

    def build(
        self, profile: RecruiterProfile, period: AnalyticsPeriod | None = None
    ) -> dict:
        if period is None:
            today = timezone.localdate()
            period = AnalyticsPeriod(
                "7d", "Last 7 Days", today - timedelta(days=6), today
            )
        apps_period = self.apps_for_period(profile, period)
        apps_all = self.all_apps(profile)
        jobs = self.jobs_qs(profile)

        has_data = apps_all.exists() or jobs.filter(status=JobStatus.PUBLISHED).exists()

        chart = ChartDataService().application_trend(apps_period, period)
        funnel = FunnelAnalyticsService().build(
            apps_period if apps_period.exists() else apps_all
        )
        metrics = HiringMetricsService().build(
            apps_period if apps_period.exists() else apps_all, jobs, profile
        )
        departments = DepartmentAnalyticsService().build(
            apps_period if apps_period.exists() else apps_all, jobs
        )

        company_ids = list(
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        highlights = self._highlights(apps_all, jobs, company_ids, today_start)
        sources = self._top_sources(apps_period if apps_period.exists() else apps_all)
        top_jobs = self._top_jobs(jobs, apps_all)

        return {
            "has_data": has_data,
            "period": period.key,
            "period_label": period.label,
            "period_options": list(self.PERIOD_OPTIONS),
            "application_trend": chart,
            "funnel": funnel,
            "metrics": metrics,
            "departments": departments,
            "highlights": highlights,
            "top_sources": sources,
            "top_jobs": top_jobs,
            "hiring_trends": self._hiring_trends(apps_all),
            "interview_trends": self._interview_trends(profile, period),
        }

    def _highlights(self, apps_qs, jobs_qs, company_ids, today_start) -> dict:
        by_status = dict(
            apps_qs.values("status").annotate(c=Count("id")).values_list("status", "c")
        )
        tomorrow = today_start + timedelta(days=1)
        upcoming = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
            scheduled_at__gte=today_start,
            status__in=(
                InterviewStatus.SCHEDULED,
                InterviewStatus.CONFIRMED,
                InterviewStatus.IN_PROGRESS,
            ),
        ).count()
        return {
            "active_jobs": jobs_qs.filter(status=JobStatus.PUBLISHED).count(),
            "closed_jobs": jobs_qs.filter(status=JobStatus.CLOSED).count(),
            "open_positions": jobs_qs.filter(
                status__in=(JobStatus.PUBLISHED, JobStatus.DRAFT)
            ).count(),
            "pending_reviews": by_status.get(JobApplicationStatus.APPLIED, 0)
            + by_status.get(JobApplicationStatus.UNDER_REVIEW, 0),
            "upcoming_interviews": upcoming,
            "pending_offers": by_status.get(JobApplicationStatus.OFFER_RELEASED, 0),
            "resume_queue": by_status.get(JobApplicationStatus.UNDER_REVIEW, 0),
            "most_applied_job": self._most_applied_job(apps_qs),
        }

    @staticmethod
    def _most_applied_job(apps_qs) -> dict | None:
        row = (
            apps_qs.values("job_posting__title")
            .annotate(c=Count("id"))
            .order_by("-c")
            .first()
        )
        if not row or not row["c"]:
            return None
        return {"title": row["job_posting__title"], "count": row["c"]}

    @staticmethod
    def _top_jobs(jobs_qs, apps_qs) -> list[dict]:
        rows = jobs_qs.filter(status=JobStatus.PUBLISHED).order_by(
            "-application_count"
        )[:5]
        return [
            {
                "id": str(j.pk),
                "title": j.title,
                "applications": j.application_count,
                "views": j.view_count,
                "hired": apps_qs.filter(
                    job_posting_id=j.pk, status=JobApplicationStatus.HIRED
                ).count(),
            }
            for j in rows
        ]

    @staticmethod
    def _top_sources(apps_qs) -> list[dict]:
        total = apps_qs.count() or 1
        rows = apps_qs.values("source").annotate(c=Count("id")).order_by("-c")[:5]
        return [
            {
                "label": SOURCE_LABELS.get(
                    r["source"] or "",
                    (r["source"] or "internal").replace("_", " ").title(),
                ),
                "count": r["c"],
                "pct": round((r["c"] / total) * 100),
            }
            for r in rows
        ]

    @staticmethod
    def _hiring_trends(apps_qs) -> dict:
        now = timezone.localdate()
        daily = []
        for i in range(6, -1, -1):
            d = now - timedelta(days=i)
            daily.append(
                {
                    "label": d.strftime("%a"),
                    "value": apps_qs.filter(
                        status=JobApplicationStatus.HIRED, hired_at__date=d
                    ).count(),
                }
            )
        weekly = []
        for w in range(3, -1, -1):
            start = now - timedelta(days=now.weekday() + 7 * w)
            end = start + timedelta(days=6)
            weekly.append(
                {
                    "label": f"W{4 - w}",
                    "value": apps_qs.filter(
                        status=JobApplicationStatus.HIRED,
                        hired_at__date__gte=start,
                        hired_at__date__lte=end,
                    ).count(),
                }
            )
        month_start = now.replace(day=1)
        monthly_total = apps_qs.filter(
            status=JobApplicationStatus.HIRED, hired_at__date__gte=month_start
        ).count()
        return {"daily": daily, "weekly": weekly, "monthly_total": monthly_total}

    @staticmethod
    def _interview_trends(profile: RecruiterProfile, period: AnalyticsPeriod) -> dict:
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .values_list("company_id", flat=True)
        )
        interviews = JobApplicationInterview.objects.filter(
            application__job_posting__company_id__in=company_ids,
            application__is_deleted=False,
            is_deleted=False,
            scheduled_at__date__gte=period.start,
            scheduled_at__date__lte=period.end,
        )
        scheduled = interviews.filter(
            status__in=(
                InterviewStatus.SCHEDULED,
                InterviewStatus.CONFIRMED,
                InterviewStatus.IN_PROGRESS,
                InterviewStatus.RESCHEDULED,
            )
        ).count()
        completed = interviews.filter(status=InterviewStatus.COMPLETED).count()
        cancelled = interviews.filter(status=InterviewStatus.CANCELLED).count()
        no_show = 0
        denominator = completed + cancelled + no_show
        success_rate = round((completed / denominator) * 100) if denominator else 0
        return {
            "scheduled": scheduled,
            "completed": completed,
            "cancelled": cancelled,
            "no_show": no_show,
            "success_rate": success_rate,
        }

    def export_rows(
        self, profile: RecruiterProfile, period: AnalyticsPeriod
    ) -> list[list[str]]:
        data = self.build(profile, period)
        rows = [["Recruitment Analytics Export"], [f"Period: {period.label}"], []]
        rows.append(["Application Trend"])
        rows.append(["Date", "Applications"])
        for p in data["application_trend"]["points"]:
            rows.append([p["date"], str(p["value"])])
        rows.append([])
        rows.append(["Hiring Funnel", "Count", "Conversion %", "Drop-off %"])
        for step in data["funnel"]:
            rows.append(
                [
                    step["label"],
                    str(step["value"]),
                    str(step["pct"]),
                    str(step["drop_off"]),
                ]
            )
        rows.append([])
        rows.append(["Metrics", "Value"])
        for m in data["metrics"]:
            rows.append([m["label"], f"{m['value']}{m.get('unit', '')}"])
        rows.append([])
        rows.append(["Department", "Jobs", "Applicants", "Hired"])
        for d in data["departments"]:
            rows.append(
                [d["label"], str(d["jobs"]), str(d["applicants"]), str(d["hired"])]
            )
        return rows
