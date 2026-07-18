"""Institution analytics and reporting portal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Sum, F
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.accounts.models.college_user import CollegeUser
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.constants.enums import ApplicationSource
from apps.applications.models import FacultyApplicationTimelineEvent
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.core.services.base import BaseService
from apps.faculty.constants.enums import VacancyStatus
from apps.faculty.selectors.vacancy_dashboard import VacancyDashboardSelector
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.notifications.models import Notification


@dataclass
class CollegeAnalyticsPortalContext:
    stats: list[dict]
    reporting: dict
    funnel: list[dict]
    vacancy_performance: list[dict]
    application_sources: dict
    trends: dict
    department_hiring: list[dict]
    response_rate: int


class CollegeAnalyticsPortalService(BaseService):
    TREND_WEEKS = 8

    def build(
        self, user: CollegeUser, period: str = "8w"
    ) -> CollegeAnalyticsPortalContext:
        app_stats = FacultyApplicationStatisticsService().college_dashboard(user)
        vacancy_stats = VacancyDashboardSelector().college_user_summary(user)
        apps = FacultyApplicationSelector().for_college_user(user)
        vacancies_qs = FacultyVacancySelector().for_college_user(user)
        by_status = app_stats.get("applications_by_status") or {}
        total = app_stats.get("total_applications") or 0
        total_or_one = total or 1

        funnel = [
            {
                "label": "Applied",
                "value": by_status.get(FacultyApplicationStatus.APPLIED, 0),
                "pct": 100,
            },
            {
                "label": "Under Review",
                "value": sum(
                    by_status.get(s, 0)
                    for s in (
                        FacultyApplicationStatus.UNDER_REVIEW,
                        FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                    )
                ),
                "pct": round(
                    sum(
                        by_status.get(s, 0)
                        for s in (
                            FacultyApplicationStatus.UNDER_REVIEW,
                            FacultyApplicationStatus.ACADEMIC_VERIFICATION,
                        )
                    )
                    / total_or_one
                    * 100
                ),
            },
            {
                "label": "Shortlisted",
                "value": sum(
                    by_status.get(s, 0)
                    for s in (
                        FacultyApplicationStatus.DEPARTMENT_REVIEW,
                        FacultyApplicationStatus.PRINCIPAL_REVIEW,
                        FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                    )
                ),
                "pct": round(
                    sum(
                        by_status.get(s, 0)
                        for s in (
                            FacultyApplicationStatus.DEPARTMENT_REVIEW,
                            FacultyApplicationStatus.PRINCIPAL_REVIEW,
                            FacultyApplicationStatus.MANAGEMENT_APPROVAL,
                        )
                    )
                    / total_or_one
                    * 100
                ),
            },
            {
                "label": "Interview",
                "value": by_status.get(FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0)
                + by_status.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0),
                "pct": round(
                    (
                        by_status.get(FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0)
                        + by_status.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0)
                    )
                    / total_or_one
                    * 100
                ),
            },
            {
                "label": "Offers",
                "value": by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
                + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0),
                "pct": round(
                    (
                        by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
                        + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0)
                    )
                    / total_or_one
                    * 100
                ),
            },
            {
                "label": "Joined",
                "value": by_status.get(FacultyApplicationStatus.JOINED, 0),
                "pct": round(
                    by_status.get(FacultyApplicationStatus.JOINED, 0)
                    / total_or_one
                    * 100
                ),
            },
        ]

        vacancies = vacancies_qs.filter(status=VacancyStatus.PUBLISHED).order_by(
            "-application_count"
        )[:8]
        vacancy_performance = [
            {
                "id": str(v.pk),
                "title": v.title,
                "applications": v.application_count,
                "views": v.view_count,
                "status": v.get_status_display()
                if hasattr(v, "get_status_display")
                else v.status,
            }
            for v in vacancies
        ]

        reviewed = apps.exclude(status=FacultyApplicationStatus.APPLIED).count()
        response_rate = round((reviewed / total_or_one) * 100) if total else 0

        offers_released = (
            by_status.get(FacultyApplicationStatus.OFFER_RELEASED, 0)
            + by_status.get(FacultyApplicationStatus.OFFER_ACCEPTED, 0)
            + by_status.get(FacultyApplicationStatus.OFFER_DECLINED, 0)
        )
        offers_accepted = by_status.get(
            FacultyApplicationStatus.OFFER_ACCEPTED, 0
        ) + by_status.get(FacultyApplicationStatus.JOINED, 0)
        interviews_done = by_status.get(FacultyApplicationStatus.INTERVIEW_COMPLETED, 0)
        interviews_total = interviews_done + by_status.get(
            FacultyApplicationStatus.INTERVIEW_SCHEDULED, 0
        )
        joined_count = by_status.get(FacultyApplicationStatus.JOINED, 0)
        profile_views = Notification.objects.filter(
            recipient_domain="college",
            recipient_id=user.pk,
            event_type__icontains="profile",
            is_deleted=False,
        ).count()
        job_views = vacancies_qs.aggregate(total=Sum("view_count"))["total"] or 0
        trends = self._trends(apps, period)
        department_hiring = self._department_hiring(apps)

        return CollegeAnalyticsPortalContext(
            stats=self._stat_cards(
                app_stats=app_stats,
                vacancy_stats=vacancy_stats,
                apps=apps,
                profile_views=profile_views,
                job_views=job_views,
                interviews_total=interviews_total,
                offers_released=offers_released,
                offers_accepted=offers_accepted,
            ),
            reporting={
                "conversion_rate": round(joined_count / total_or_one * 100),
                "offer_acceptance_rate": round(offers_accepted / offers_released * 100)
                if offers_released
                else 0,
                "interview_completion_rate": round(
                    interviews_done / interviews_total * 100
                )
                if interviews_total
                else 0,
                "active_applications": app_stats.get("active_applications", 0),
                "hiring_rate": round(joined_count / total_or_one * 100),
                "interview_rate": round(interviews_total / total_or_one * 100),
                "offers_sent": offers_released,
                "hired_candidates": joined_count,
            },
            funnel=funnel,
            vacancy_performance=vacancy_performance,
            application_sources=self._application_sources(apps),
            trends=trends,
            department_hiring=department_hiring,
            response_rate=response_rate,
        )

    @staticmethod
    def _stat_cards(
        *,
        app_stats: dict,
        vacancy_stats: dict,
        apps,
        profile_views: int,
        job_views: int,
        interviews_total: int,
        offers_released: int,
        offers_accepted: int,
    ) -> list[dict]:
        today_start = timezone.localtime().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        new_today = apps.filter(applied_at__gte=today_start).count()
        total_applications = app_stats.get("total_applications", 0)
        total_or_one = total_applications or 1
        joined_count = (app_stats.get("applications_by_status") or {}).get(
            FacultyApplicationStatus.JOINED, 0
        )
        return [
            {
                "key": "total_jobs",
                "label": "Total Jobs",
                "value": str(vacancy_stats.get("total_vacancies", 0)),
                "icon": "bi-mortarboard",
                "tone": "primary",
            },
            {
                "key": "total_applications",
                "label": "Total Applications",
                "value": str(app_stats.get("total_applications", 0)),
                "icon": "bi-people",
                "tone": "secondary",
            },
            {
                "key": "hiring_rate",
                "label": "Hiring Rate",
                "value": f"{round(joined_count / total_or_one * 100)}%",
                "icon": "bi-activity",
                "tone": "accent",
            },
            {
                "key": "interview_rate",
                "label": "Interview Rate",
                "value": f"{round(interviews_total / total_or_one * 100)}%",
                "icon": "bi-inbox",
                "tone": "tertiary",
            },
            {
                "key": "offer_acceptance",
                "label": "Offer Acceptance",
                "value": f"{round(offers_accepted / offers_released * 100) if offers_released else 0}%",
                "icon": "bi-envelope-check",
                "tone": "success",
            },
            {
                "key": "profile_views",
                "label": "Profile Views",
                "value": str(profile_views),
                "icon": "bi-person-lines-fill",
                "tone": "secondary",
            },
            {
                "key": "job_views",
                "label": "Job Views",
                "value": str(job_views),
                "icon": "bi-eye",
                "tone": "primary",
            },
            {
                "key": "new_today",
                "label": "Applications Today",
                "value": str(new_today),
                "icon": "bi-calendar-day",
                "tone": "tertiary",
            },
        ]

    @staticmethod
    def _application_sources(apps) -> dict:
        source_counts = dict(
            apps.values("source").annotate(c=Count("id")).values_list("source", "c")
        )
        total = sum(source_counts.values())
        if total == 0:
            return {"segments": []}
        tone_map = {
            ApplicationSource.DIRECT: "primary",
            ApplicationSource.REFERRAL: "accent",
            ApplicationSource.JOB_BOARD: "secondary",
        }
        segments = []
        for choice in ApplicationSource:
            count = source_counts.get(choice.value, 0)
            if count == 0:
                continue
            segments.append(
                {
                    "label": choice.label,
                    "count": count,
                    "pct": round(count / total * 100),
                    "tone": tone_map.get(choice.value, "primary"),
                }
            )
        return {"segments": segments}

    def _trends(self, apps, period: str) -> dict:
        now = timezone.localtime()
        if period == "7d":
            days_back = 7
            group_by = "day"
        elif period == "30d":
            days_back = 30
            group_by = "day"
        elif period == "3m":
            days_back = 90
            group_by = "week"
        elif period == "1y":
            days_back = 365
            group_by = "month"
        else:
            days_back = 56  # 8w default
            group_by = "week"

        start_day = (now - timedelta(days=days_back)).date()

        def get_bucket(d):
            if group_by == "day":
                return d
            elif group_by == "week":
                return d - timedelta(days=d.weekday())
            elif group_by == "month":
                return d.replace(day=1)
            return d

        app_counts = (
            apps.filter(applied_at__date__gte=start_day)
            .annotate(day=TruncDate("applied_at"))
            .values("day")
            .annotate(value=Count("id"))
            .order_by("day")
        )
        trend = {}
        for row in app_counts:
            day = row.get("day")
            if day:
                bkt = get_bucket(day)
                trend[bkt] = trend.get(bkt, 0) + int(row.get("value") or 0)

        app_ids = apps.values_list("id", flat=True)
        interview_events = (
            FacultyApplicationTimelineEvent.objects.filter(
                application_id__in=app_ids,
                to_status__in=(
                    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                    FacultyApplicationStatus.INTERVIEW_COMPLETED,
                ),
                occurred_at__date__gte=start_day,
            )
            .annotate(day=TruncDate("occurred_at"))
            .values("day")
            .annotate(value=Count("id"))
            .order_by("day")
        )
        interview_map = {}
        for row in interview_events:
            day = row.get("day")
            if day:
                bkt = get_bucket(day)
                interview_map[bkt] = interview_map.get(bkt, 0) + int(
                    row.get("value") or 0
                )

        cancelled = 0
        no_show = 0

        # completed vs total to calculate success rate overall
        completed_interviews = FacultyApplicationTimelineEvent.objects.filter(
            application_id__in=app_ids,
            to_status=FacultyApplicationStatus.INTERVIEW_COMPLETED,
            occurred_at__date__gte=start_day,
        ).count()

        hiring_events = (
            FacultyApplicationTimelineEvent.objects.filter(
                application_id__in=app_ids,
                to_status=FacultyApplicationStatus.JOINED,
                occurred_at__date__gte=start_day,
            )
            .annotate(day=TruncDate("occurred_at"))
            .values("day")
            .annotate(value=Count("id"))
            .order_by("day")
        )
        hiring_map = {}
        for row in hiring_events:
            day = row.get("day")
            if day:
                bkt = get_bucket(day)
                hiring_map[bkt] = hiring_map.get(bkt, 0) + int(row.get("value") or 0)

        labels = []
        applications = []
        interviews = []
        hires = []

        current_d = start_day
        end_d = now.date()

        if group_by == "day":
            while current_d <= end_d:
                labels.append(current_d.strftime("%d %b"))
                applications.append(trend.get(current_d, 0))
                interviews.append(interview_map.get(current_d, 0))
                hires.append(hiring_map.get(current_d, 0))
                current_d += timedelta(days=1)
        elif group_by == "week":
            current_d = get_bucket(start_day)
            while current_d <= end_d:
                labels.append(current_d.strftime("%d %b"))
                applications.append(trend.get(current_d, 0))
                interviews.append(interview_map.get(current_d, 0))
                hires.append(hiring_map.get(current_d, 0))
                current_d += timedelta(days=7)
        elif group_by == "month":
            current_d = get_bucket(start_day)
            while current_d <= end_d:
                labels.append(current_d.strftime("%b %Y"))
                applications.append(trend.get(current_d, 0))
                interviews.append(interview_map.get(current_d, 0))
                hires.append(hiring_map.get(current_d, 0))
                if current_d.month == 12:
                    current_d = current_d.replace(year=current_d.year + 1, month=1)
                else:
                    current_d = current_d.replace(month=current_d.month + 1)

        return {
            "labels": labels,
            "applications": applications,
            "interviews": interviews,
            "hiring": hires,
            "interview_stats": {
                "cancelled": cancelled,
                "no_show": no_show,
                "completed": completed_interviews,
            },
        }

    @staticmethod
    def _department_hiring(apps) -> list[dict]:
        rows = (
            apps.filter(status=FacultyApplicationStatus.JOINED)
            .values("department")
            .annotate(value=Count("id"))
            .order_by("-value", "department")[:8]
        )
        peak = rows[0]["value"] if rows else 0
        result = []
        for row in rows:
            label = row.get("department") or "Unspecified"
            value = int(row.get("value") or 0)
            pct = round((value / peak) * 100) if peak else 0
            result.append({"label": label, "value": value, "pct": pct})
        return result
