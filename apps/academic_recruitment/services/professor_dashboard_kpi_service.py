"""Live KPI calculations for the Faculty Job Seeker dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone

from apps.academic_recruitment.models import ProfessorProfile
from apps.academic_recruitment.services.professor_profile_completion_service import (
    ProfessorProfileCompletionService,
)
from apps.academic_recruitment.services.professor_vacancy_recommendation_service import (
    ProfessorVacancyRecommendationService,
)
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.applications.models import FacultyApplication
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.core.services.base import BaseService
from apps.faculty.models import SavedVacancy
from apps.notifications.models import Notification

SUCCESS_STATUSES = (
    FacultyApplicationStatus.OFFER_RELEASED,
    FacultyApplicationStatus.OFFER_ACCEPTED,
    FacultyApplicationStatus.JOINED,
)

UNDER_REVIEW_STATUSES = {
    FacultyApplicationStatus.APPLIED,
    FacultyApplicationStatus.UNDER_REVIEW,
    FacultyApplicationStatus.ACADEMIC_VERIFICATION,
    FacultyApplicationStatus.DEPARTMENT_REVIEW,
    FacultyApplicationStatus.PRINCIPAL_REVIEW,
    FacultyApplicationStatus.MANAGEMENT_APPROVAL,
}


@dataclass
class DashboardKPIBundle:
    profile_completion: int
    profile_strength_score: int
    institution_interest_score: int
    application_success_rate: int
    profile_visibility_change: int
    matching_jobs_total: int
    applications_total: int
    applications_under_review: int
    applications_shortlisted: int
    interview_pending: int
    profile_views_total: int
    profile_views_today: int
    saved_jobs_total: int
    activity_insights: list[str] = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "profile_completion": self.profile_completion,
            "profile_strength_score": self.profile_strength_score,
            "institution_interest_score": self.institution_interest_score,
            "application_success_rate": self.application_success_rate,
            "profile_visibility_change": self.profile_visibility_change,
            "matching_jobs_total": self.matching_jobs_total,
            "applications_total": self.applications_total,
            "applications_under_review": self.applications_under_review,
            "applications_shortlisted": self.applications_shortlisted,
            "interview_pending": self.interview_pending,
            "profile_views_total": self.profile_views_total,
            "profile_views_today": self.profile_views_today,
            "saved_jobs_total": self.saved_jobs_total,
            "activity_insights": self.activity_insights,
            "updated_at": self.updated_at,
        }


class ProfessorDashboardKPIService(BaseService):
    """Compute real-time faculty dashboard metrics from database activity."""

    def build(self, profile: ProfessorProfile) -> DashboardKPIBundle:
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        prev_week_start = now - timedelta(days=14)

        completion = ProfessorProfileCompletionService().get_dashboard_state(profile)
        stats = FacultyApplicationStatisticsService().professor_dashboard(profile)
        by_status = stats.get("applications_by_status", {})

        applications = FacultyApplication.objects.filter(
            professor=profile, is_deleted=False
        )
        apps_total = stats.get("total_applications", 0)
        under_review = sum(by_status.get(s, 0) for s in UNDER_REVIEW_STATUSES)
        shortlisted = sum(
            by_status.get(s, 0)
            for s in (
                FacultyApplicationStatus.DEPARTMENT_REVIEW,
                FacultyApplicationStatus.PRINCIPAL_REVIEW,
                FacultyApplicationStatus.MANAGEMENT_APPROVAL,
            )
        )
        interview_pending = applications.filter(
            status=FacultyApplicationStatus.INTERVIEW_SCHEDULED
        ).count()
        success_count = sum(by_status.get(s, 0) for s in SUCCESS_STATUSES)
        success_rate = round((success_count / apps_total) * 100) if apps_total else 0

        saved_total = SavedVacancy.objects.filter(
            professor=profile, is_deleted=False
        ).count()
        views_qs = Notification.objects.filter(
            recipient_domain="professor",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
        )
        views_total = views_qs.count()
        views_today = views_qs.filter(created_at__gte=today_start).count()
        views_this_week = views_qs.filter(created_at__gte=week_start).count()
        views_prev_week = views_qs.filter(
            created_at__gte=prev_week_start, created_at__lt=week_start
        ).count()
        visibility_change = self._percent_change(views_this_week, views_prev_week)

        matching_total = len(
            ProfessorVacancyRecommendationService().recommend(profile, limit=50)
        )
        strength = min(99, completion.percentage + (10 if profile.cv_file_id else 0))

        institution_interest = min(
            100,
            int(
                min(views_this_week * 10, 40)
                + min(shortlisted * 8, 24)
                + min(interview_pending * 12, 24)
                + completion.percentage * 0.12
            ),
        )

        insights = self._activity_insights(
            profile, today_start, cutoff=now - timedelta(days=14)
        )

        return DashboardKPIBundle(
            profile_completion=completion.percentage,
            profile_strength_score=strength,
            institution_interest_score=institution_interest,
            application_success_rate=success_rate,
            profile_visibility_change=visibility_change,
            matching_jobs_total=matching_total,
            applications_total=apps_total,
            applications_under_review=under_review,
            applications_shortlisted=shortlisted,
            interview_pending=interview_pending,
            profile_views_total=views_total,
            profile_views_today=views_today,
            saved_jobs_total=saved_total,
            activity_insights=insights,
            updated_at=timezone.localtime(now).strftime("%b %d, %I:%M %p"),
        )

    @staticmethod
    def _percent_change(current: int, previous: int) -> int:
        if previous == 0:
            return 100 if current > 0 else 0
        return round(((current - previous) / previous) * 100)

    @staticmethod
    def _activity_insights(
        profile: ProfessorProfile, today_start, *, cutoff, limit: int = 6
    ) -> list[str]:
        updates: list[tuple] = []
        seen: set[str] = set()

        def add(when, text: str) -> None:
            cleaned = " ".join((text or "").split())
            if not cleaned or cleaned in seen:
                return
            seen.add(cleaned)
            updates.append((when, cleaned))

        for notif in Notification.objects.filter(
            recipient_domain="professor",
            recipient_id=profile.user_id,
            created_at__gte=cutoff,
        ).order_by("-created_at")[: limit * 2]:
            add(notif.created_at, notif.body or notif.title)

        views_today = Notification.objects.filter(
            recipient_domain="professor",
            recipient_id=profile.user_id,
            event_type="profile_viewed",
            created_at__gte=today_start,
        ).count()
        if views_today > 0:
            add(
                timezone.now(),
                f"{views_today} institution{'s' if views_today != 1 else ''} viewed your profile today.",
            )

        updates.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in updates[:limit]]
