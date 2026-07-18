"""In-app notifications for job recommendation events."""

from __future__ import annotations

from django.utils import timezone

from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService
from apps.it_recruitment.models import JobSeekerProfile, JobSeekerRecommendationSnapshot
from apps.jobs.models import JobPosting


class JobRecommendationNotificationService(BaseService):
    """Publish outbox events when matching jobs are found."""

    def __init__(self):
        self.outbox = OutboxService()

    def notify_preference_rebuild(
        self,
        profile: JobSeekerProfile,
        snapshot: JobSeekerRecommendationSnapshot,
        *,
        top_jobs: list[tuple[JobPosting, int]],
    ) -> None:
        if snapshot.new_matches_count <= 0:
            return

        roles = (
            profile.preferred_roles if isinstance(profile.preferred_roles, list) else []
        )
        role_label = roles[0] if roles else (profile.headline or "your profile")

        if snapshot.new_matches_count == 1 and top_jobs:
            job = top_jobs[0][0]
            location = job.city or job.location or "your preferred location"
            body = (
                f"A new {job.title} position was posted in {location} "
                f"matching your career preferences."
            )
        elif snapshot.new_matches_count > 1:
            body = (
                f"{snapshot.new_matches_count} new {role_label} jobs match your profile. "
                f"{snapshot.total_matches} total opportunities are waiting for you."
            )
        else:
            body = f"We found {snapshot.total_matches} jobs aligned with your career preferences."

        self._publish(
            profile=profile,
            event_type="job.recommended",
            title="New job matches for you",
            body=body,
            extra={
                "total_matches": snapshot.total_matches,
                "new_matches_count": snapshot.new_matches_count,
                "top_match_score": snapshot.top_match_score,
            },
        )
        snapshot.last_notified_at = timezone.now()
        snapshot.save(update_fields=["last_notified_at", "updated_at"])

    def notify_single_job_match(
        self,
        profile: JobSeekerProfile,
        job: JobPosting,
        *,
        match_score: int,
    ) -> None:
        work_mode = job.get_work_mode_display() if job.work_mode else ""
        if job.is_remote or job.work_mode == "remote":
            body = f"Your preferred remote role is now available: {job.title} at {job.company_name_snapshot}."
        elif work_mode:
            body = (
                f"A new {job.title} position ({work_mode}) was posted — "
                f"{match_score}% match with your profile."
            )
        else:
            body = f"A new {job.title} position was posted — {match_score}% match with your profile."

        self._publish(
            profile=profile,
            event_type="job.recommended",
            title="New matching job posted",
            body=body,
            extra={
                "job_posting_id": str(job.pk),
                "match_score": match_score,
            },
        )

    def _publish(
        self,
        *,
        profile: JobSeekerProfile,
        event_type: str,
        title: str,
        body: str,
        extra: dict | None = None,
    ) -> None:
        payload = {
            "recipient_domain": "it",
            "recipient_id": str(profile.user_id),
            "title": title,
            "body": body,
        }
        if extra:
            payload.update(extra)
        self.outbox.publish(
            domain=DomainType.IT,
            event_type=event_type,
            aggregate_type="it_job_seeker_profile",
            aggregate_id=profile.pk,
            payload=payload,
        )

    @staticmethod
    def deliver_pending_notifications(limit: int = 10) -> int:
        """Process outbox so in-app notifications appear immediately."""
        from apps.notifications.services.outbox_processor import OutboxProcessorService

        return OutboxProcessorService().process_batch(limit=limit)
