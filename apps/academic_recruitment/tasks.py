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
    from apps.academic_recruitment.models.professor import ProfessorProfile
    from apps.academic_recruitment.models.resume import ParsedResume, ParsedResumeStatus
    from apps.documents.models import StoredFile
    from apps.documents.services.storage_service import StorageService
    import pypdf
    import re
    
    try:
        profile = ProfessorProfile.objects.get(pk=profile_id)
        cv_file = StoredFile.objects.get(pk=file_id)
        
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

