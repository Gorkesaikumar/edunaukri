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
        
        parsed, _ = ParsedResume.objects.get_or_create(profile=profile, cv_file=cv_file)
        parsed.status = ParsedResumeStatus.PROCESSING
        parsed.save(update_fields=["status"])
        
        storage = StorageService()
        path = storage.get_absolute_path(cv_file)
        text = ""
        
        try:
            with path.open("rb") as f:
                reader = pypdf.PdfReader(f)
                text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
        except Exception as read_exc:
            logger.exception("Failed to read PDF")
            parsed.status = ParsedResumeStatus.FAILED
            parsed.error_message = str(read_exc)
            parsed.save(update_fields=["status", "error_message"])
            return {"status": "failed", "error": "PDF extraction failed"}
            
        parsed.raw_text = text
        
        # Super simple extraction logic based on keywords
        skills = []
        knowledge_base = ["python", "django", "java", "c++", "machine learning", "ai", "react", "html", "css", "javascript", "linux", "aws", "data science", "nlp", "sql"]
        text_lower = text.lower()
        for skill in knowledge_base:
            if re.search(r'\b' + re.escape(skill) + r'\b', text_lower):
                skills.append(skill.title())
        
        degrees = []
        if re.search(r'\b(phd|ph\.d|doctorate)\b', text_lower):
            degrees.append("Ph.D")
        if re.search(r'\b(master|msc|m\.sc|mtech|m\.tech|m\.e)\b', text_lower):
            degrees.append("Master's")
        if re.search(r'\b(bachelor|bsc|b\.sc|btech|b\.tech|b\.e)\b', text_lower):
            degrees.append("Bachelor's")
            
        parsed.extracted_skills = skills
        parsed.extracted_education = degrees
        parsed.status = ParsedResumeStatus.SUCCESS
        parsed.save(update_fields=["status", "raw_text", "extracted_skills", "extracted_education"])
        
        # Trigger recommendation recalculation (which invalidates cache)
        from apps.academic_recruitment.services.professor_profile_completion_service import ProfessorProfileCompletionService
        ProfessorProfileCompletionService().recalculate(profile)
        
        return {"status": "success", "skills_found": len(skills)}
    except Exception as exc:
        logger.exception("Resume parsing failed entirely")
        raise self.retry(exc=exc) from exc

