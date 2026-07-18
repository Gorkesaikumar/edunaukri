"""Celery tasks for IT Recruitment recommendation engine."""

from __future__ import annotations

import logging

from celery import shared_task
from apps.core.tasks import BaseTask
from apps.core.utils.locking import redis_lock


logger = logging.getLogger(__name__)


@shared_task(
    base=BaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=330,
)
def rebuild_seeker_recommendations_task(
    self, profile_id: str, reason: str = "background", notify: bool = True
):
    """Rebuild cached recommendations for a single job seeker."""
    from apps.it_recruitment.services.job_recommendation_engine_service import (
        JobRecommendationEngineService,
    )

    try:
        summary = JobRecommendationEngineService().rebuild_for_seeker(
            profile_id,
            reason=reason,
            notify=notify,
        )
        return summary.to_dict()
    except Exception as exc:
        logger.exception("Seeker recommendation rebuild failed for %s", profile_id)
        raise self.retry(exc=exc) from exc


@shared_task(
    base=BaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
def rebuild_recommendations_for_job_task(
    self, job_id: str, reason: str = "job_published"
):
    """Score a newly published job against all active seekers."""
    from apps.it_recruitment.services.job_recommendation_engine_service import (
        JobRecommendationEngineService,
    )

    try:
        count = JobRecommendationEngineService().score_job_for_all_seekers(
            job_id, notify=True
        )
        return {"job_id": job_id, "seekers_updated": count, "reason": reason}
    except Exception as exc:
        logger.exception("Job recommendation rebuild failed for %s", job_id)
        raise self.retry(exc=exc) from exc


@shared_task(
    base=BaseTask,
    name="it_recruitment.scan_expiring_certificates",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
def scan_expiring_certificates_task(self, batch_size: int = 200):
    """Notify job seekers about certificates expiring within the configured window."""
    from apps.it_recruitment.services.certificate_expiry_notification_service import (
        CertificateExpiryNotificationService,
    )

    try:
        count = CertificateExpiryNotificationService().scan_and_notify(
            batch_size=batch_size
        )
        return {"notified": count}
    except Exception as exc:
        logger.exception("Certificate expiry scan failed")
        raise self.retry(exc=exc) from exc


@shared_task(
    base=BaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=20,
    soft_time_limit=300,
    time_limit=330,
)
def parse_resume_task(self, stored_file_id: str, profile_id: str):
    """Asynchronously re-parse resume, refresh analysis, rebuild matches, notify improvements."""
    from apps.documents.models import StoredFile
    from apps.it_recruitment.models import JobSeekerProfile
    from apps.it_recruitment.services.job_recommendation_engine_service import (
        JobRecommendationEngineService,
    )
    from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
        JobSeekerResumeAnalysisService,
    )
    from apps.it_recruitment.services.resume_match_notification_service import (
        ResumeMatchNotificationService,
    )
    from apps.it_recruitment.services.resume_parsing_service import ResumeParsingService

    try:
        stored = StoredFile.objects.filter(pk=stored_file_id, is_deleted=False).first()
        profile = JobSeekerProfile.objects.filter(
            pk=profile_id, is_deleted=False
        ).first()
        if not stored or not profile:
            return {"status": "skipped"}

        previous_score = ResumeMatchNotificationService().current_match_score(profile)
        ResumeParsingService().parse_and_store(stored, profile=profile)
        JobSeekerResumeAnalysisService().get_analysis(profile, force_refresh=True)
        JobRecommendationEngineService().rebuild_for_seeker(
            profile_id,
            reason="resume_parsed",
            notify=True,
        )
        profile.refresh_from_db()
        ResumeMatchNotificationService().notify_if_improved(profile, previous_score)
        return {"status": "ok", "file_id": str(stored_file_id)}
    except Exception as exc:
        logger.exception("Resume parse failed for %s", stored_file_id)
        raise self.retry(exc=exc) from exc
