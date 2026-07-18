"""Certificate category and status helpers for job seeker certifications."""

from django.db import models


class CertificateCategory(models.TextChoices):
    TECHNICAL = "technical", "Technical"
    PROFESSIONAL = "professional", "Professional"
    ACADEMIC = "academic", "Academic"
    LANGUAGE = "language", "Language"
    COMPLIANCE = "compliance", "Compliance"
    OTHER = "other", "Other"


EXPIRING_SOON_DAYS = 60
