"""Notifications when resume match score improves after upload or autofill."""

from __future__ import annotations

from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.job_recommendation_cache_service import (
    JobRecommendationCacheService,
)
from apps.it_recruitment.services.jobseeker_dashboard_kpi_service import (
    JobSeekerDashboardKPIService,
)
from apps.notifications.services.outbox_processor import OutboxProcessorService


class ResumeMatchNotificationService(BaseService):
    IMPROVEMENT_THRESHOLD = 3

    def current_match_score(self, profile: JobSeekerProfile) -> int:
        snapshot = JobRecommendationCacheService().get_snapshot(profile)
        if snapshot and snapshot.top_match_score:
            return snapshot.top_match_score
        kpis = JobSeekerDashboardKPIService().build(profile)
        return kpis.resume_match_score

    def notify_if_improved(
        self, profile: JobSeekerProfile, previous_score: int
    ) -> None:
        new_score = self.current_match_score(profile)
        if new_score - previous_score < self.IMPROVEMENT_THRESHOLD:
            return

        OutboxService().publish(
            domain=DomainType.IT,
            event_type="resume.match_improved",
            aggregate_type="job_seeker_profile",
            aggregate_id=profile.pk,
            payload={
                "recipient_domain": "it",
                "recipient_id": str(profile.user_id),
                "title": "Resume match score improved",
                "body": (
                    f"Your resume match score increased from {previous_score}% to {new_score}%. "
                    "Check your dashboard for better job matches."
                ),
            },
        )
        try:
            OutboxProcessorService().process_batch(limit=5)
        except Exception:
            pass
