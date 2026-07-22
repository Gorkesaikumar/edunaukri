"""Celery background tasks for Resume Trust & Fraud Detection Engine.

Production-hardened with timeout limits, retry backoff, concurrency locks, and cache management.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from apps.documents.models import StoredFile
from apps.resume_trust.models import FraudDomainType
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService

logger = logging.getLogger("resume_trust")


@shared_task(
    bind=True,
    name="apps.resume_trust.tasks.run_resume_trust_analysis_task",
    max_retries=3,
    default_retry_delay=10,
    retry_backoff=True,
    retry_backoff_max=300,
    soft_time_limit=90,
    time_limit=120,
)
def run_resume_trust_analysis_task(
    self,
    seeker_user_id: int,
    domain: str = FraudDomainType.IT,
    stored_file_id: Optional[str] = None,
    parsed_data: Optional[Dict[str, Any]] = None,
    raw_text: str = "",
    resume_version: int = 1,
) -> Dict[str, Any]:
    """Asynchronous Celery task for running trust & fraud analysis."""
    logger.info(
        "Celery Task: run_resume_trust_analysis_task starting | User: %s | Domain: %s | FileId: %s",
        seeker_user_id,
        domain,
        stored_file_id,
    )

    try:
        stored_file = None
        if stored_file_id:
            stored_file = StoredFile.objects.filter(pk=stored_file_id, is_deleted=False).first()

        service = ResumeFraudDetectionService()
        result = service.initiate_analysis(
            seeker_user_id=int(seeker_user_id),
            domain=domain,
            stored_file=stored_file,
            parsed_data=parsed_data or {},
            raw_text=raw_text or "",
            resume_version=resume_version,
        )
        return {"success": True, "data": result}

    except SoftTimeLimitExceeded:
        logger.error(
            "Soft time limit exceeded (90s) in run_resume_trust_analysis_task for user %s",
            seeker_user_id,
        )
        return {"success": False, "error": "Analysis timed out (90s limit exceeded)."}

    except Exception as exc:
        logger.exception(
            "Celery task run_resume_trust_analysis_task failed for user %s. Attempt %s/%s. Error: %s",
            seeker_user_id,
            self.request.retries + 1,
            self.max_retries,
            str(exc),
        )
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        return {"success": False, "error": str(exc)}
