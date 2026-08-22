"""Celery tasks for Academic Recruitment."""

from __future__ import annotations

import logging

from celery import shared_task
from apps.core.tasks import BaseTask
from apps.core.utils.locking import redis_lock


logger = logging.getLogger(__name__)


@shared_task(
    base=BaseTask,
    name="academic_recruitment.scan_expiring_certificates",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
def scan_expiring_professor_certificates_task(self, batch_size: int = 200):
    """Notify faculty job seekers about certificates expiring within the configured window."""
    from apps.academic_recruitment.services.professor_certificate_expiry_notification_service import (
        ProfessorCertificateExpiryNotificationService,
    )

    try:
        count = ProfessorCertificateExpiryNotificationService().scan_and_notify(
            batch_size=batch_size
        )
        return {"notified": count}
    except Exception as exc:
        logger.exception("Professor certificate expiry scan failed")
        raise self.retry(exc=exc) from exc

@shared_task(
    base=BaseTask,
    name="academic_recruitment.parse_faculty_resume_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=330,
)
def parse_faculty_resume_task(self, profile_id: int, file_id: int):
    """Extract information from resume and map to ProfessorProfile using ParsedResume model."""
    from django.core.exceptions import ObjectDoesNotExist
    from apps.academic_recruitment.models.professor import ProfessorProfile
    from apps.documents.models import StoredFile

    try:
        profile = ProfessorProfile.objects.get(pk=profile_id)
    except ObjectDoesNotExist:
        # Profile was deleted — discard this task, do not retry.
        logger.warning("parse_faculty_resume_task: profile %s not found, aborting.", profile_id)
        return {"status": "aborted", "reason": "profile_not_found"}

    try:
        cv_file = StoredFile.objects.get(pk=file_id)
    except ObjectDoesNotExist:
        # File was replaced or deleted before this task ran — abort, do not retry.
        logger.warning(
            "parse_faculty_resume_task: StoredFile %s not found for profile %s, aborting.",
            file_id, profile_id,
        )
        return {"status": "aborted", "reason": "file_not_found"}

    # Guard: if the profile's current cv_file differs from this task's file_id,
    # a newer upload already superseded this one — abort to avoid overwriting it.
    profile.refresh_from_db(fields=["cv_file"])
    if str(profile.cv_file_id) != str(file_id):
        logger.warning(
            "parse_faculty_resume_task: profile %s now has cv_file %s, task file %s is stale, aborting.",
            profile_id, profile.cv_file_id, file_id,
        )
        return {"status": "aborted", "reason": "superseded_by_newer_upload"}

    # Acquire a per-profile distributed lock so concurrent retries cannot race on
    # the same profile's ParsedResume row.
    from django.core.cache import cache
    lock_key = f"lock:parse_faculty_resume:{profile_id}"
    acquired = cache.add(lock_key, "1", timeout=290)
    if not acquired:
        logger.warning(
            "parse_faculty_resume_task: could not acquire lock for profile %s; "
            "another worker is already processing this profile. Aborting.",
            profile_id,
        )
        return {"status": "aborted", "reason": "lock_not_acquired"}

    try:
        # Re-check staleness after acquiring the lock (another instance may have
        # just finished processing a newer file while we were waiting).
        profile.refresh_from_db(fields=["cv_file"])
        if str(profile.cv_file_id) != str(file_id):
            logger.warning(
                "parse_faculty_resume_task: stale after lock acquire for profile %s, aborting.",
                profile_id,
            )
            return {"status": "aborted", "reason": "superseded_by_newer_upload"}

        from apps.resume_trust.services.resume_trust_pipeline_service import (
            ResumeTrustPipelineService,
        )
        pipeline_res = ResumeTrustPipelineService().execute_pipeline(
            profile=profile,
            stored_file=cv_file,
            domain="faculty",
        )
        return {"status": "success", "trust_report": pipeline_res.get("trust_report")}
    except Exception as exc:
        logger.exception("Resume parsing failed entirely")
        raise self.retry(exc=exc) from exc
    finally:
        cache.delete(lock_key)

