from django.db import models
from apps.core.models.base import AuditedBaseModel
from apps.academic_recruitment.models.professor import ProfessorProfile
from apps.documents.models import StoredFile

class ParsedResumeStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"

class ParsedResume(AuditedBaseModel):
    profile = models.OneToOneField(
        ProfessorProfile,
        on_delete=models.CASCADE,
        related_name="parsed_resume",
    )
    cv_file = models.ForeignKey(
        StoredFile,
        on_delete=models.CASCADE,
        related_name="parsed_resumes",
    )
    status = models.CharField(
        max_length=20,
        choices=ParsedResumeStatus.choices,
        default=ParsedResumeStatus.PENDING,
    )
    
    extracted_skills = models.JSONField(default=list, blank=True)
    extracted_education = models.JSONField(default=list, blank=True)
    extracted_experience = models.JSONField(default=list, blank=True)
    extracted_headline = models.CharField(max_length=255, blank=True)
    
    raw_text = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "faculty_parsed_resume"

    def __str__(self):
        return f"Parsed Resume for {self.profile.full_name}"
