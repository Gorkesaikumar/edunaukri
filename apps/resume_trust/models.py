"""Production-grade database schema for Resume Trust & Fraud Detection Engine."""

import uuid
from django.db import models


class FraudDomainType(models.TextChoices):
    IT = "it", "IT Recruitment"
    FACULTY = "faculty", "Faculty Recruitment"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low Risk"
    MEDIUM = "MEDIUM", "Medium Risk"
    HIGH = "HIGH", "High Risk"
    CRITICAL = "CRITICAL", "Critical Risk"


class AnalysisRecommendation(models.TextChoices):
    PASS = "PASS", "Pass"
    FLAG_FOR_REVIEW = "FLAG_FOR_REVIEW", "Flag for Review"
    REJECT = "REJECT", "Reject"


class AnalysisStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PROCESSING = "PROCESSING", "Processing"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"


class SeverityLevel(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class ResumeFraudAnalysis(models.Model):
    """Master record storing trust and fraud analysis results for candidate resume uploads."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    domain = models.CharField(
        max_length=20, choices=FraudDomainType.choices, default=FraudDomainType.IT, db_index=True
    )
    seeker_user_id = models.CharField(max_length=64, db_index=True, help_text="User ID or UUID of candidate")
    stored_file = models.ForeignKey(
        "documents.StoredFile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fraud_analyses",
        help_text="Reference to the uploaded file",
    )
    resume_version = models.PositiveIntegerField(default=1, help_text="Incrementing version count")
    trust_score = models.PositiveSmallIntegerField(default=100, help_text="Computed trust score (0 to 100)")
    risk_score = models.PositiveSmallIntegerField(default=0, help_text="Computed risk score (0 to 100)")
    confidence_score = models.DecimalField(
        max_digits=4, decimal_places=2, default=1.00, help_text="Engine confidence level (0.00 to 1.00)"
    )
    risk_level = models.CharField(
        max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW, db_index=True
    )
    warning_count = models.PositiveSmallIntegerField(default=0, help_text="Total active warning count")
    recommendation = models.CharField(
        max_length=30, choices=AnalysisRecommendation.choices, default=AnalysisRecommendation.PASS
    )
    analysis_duration_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text="Execution time in milliseconds"
    )
    json_analysis_report = models.JSONField(
        default=dict, blank=True, help_text="Full detailed JSON analysis report and evidence breakdown"
    )
    status = models.CharField(
        max_length=20, choices=AnalysisStatus.choices, default=AnalysisStatus.PENDING, db_index=True
    )
    error_message = models.TextField(blank=True, help_text="Error message if analysis failed")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resume Fraud Analysis"
        verbose_name_plural = "Resume Fraud Analyses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["domain", "seeker_user_id"]),
            models.Index(fields=["stored_file"]),
            models.Index(fields=["risk_level"]),
            models.Index(fields=["trust_score"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Fraud Analysis [{self.domain.upper()}] User:{self.seeker_user_id} - Score:{self.trust_score} ({self.risk_level})"


class ResumeFraudWarning(models.Model):
    """Granular warning flag generated during fraud analysis."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fraud_analysis = models.ForeignKey(
        ResumeFraudAnalysis, on_delete=models.CASCADE, related_name="warnings"
    )
    rule_code = models.CharField(max_length=60, db_index=True, help_text="Rule identifier")
    rule_name = models.CharField(max_length=150)
    severity = models.CharField(
        max_length=20, choices=SeverityLevel.choices, default=SeverityLevel.LOW
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    evidence_snippet = models.TextField(blank=True, help_text="Extracted text evidence")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resume Fraud Warning"
        verbose_name_plural = "Resume Fraud Warnings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["fraud_analysis", "severity"]),
            models.Index(fields=["rule_code"]),
        ]

    def __str__(self):
        return f"Warning [{self.rule_code}] - {self.title} ({self.severity})"


class ResumeFraudRule(models.Model):
    """Rule registry storing rule definitions and penalty weights."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule_code = models.CharField(max_length=60, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100, help_text="Category e.g., Timeline, Formatting, AI_Gen")
    default_weight = models.PositiveSmallIntegerField(default=10, help_text="Risk penalty weight")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Resume Fraud Rule"
        verbose_name_plural = "Resume Fraud Rules"
        ordering = ["rule_code"]

    def __str__(self):
        return f"Rule [{self.rule_code}] {self.name} (Weight: {self.default_weight})"


class ResumeFraudHistory(models.Model):
    """Audit log tracking trust score progression over time for candidate uploads."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fraud_analysis = models.ForeignKey(
        ResumeFraudAnalysis, on_delete=models.CASCADE, related_name="history_logs"
    )
    seeker_user_id = models.CharField(max_length=64, db_index=True)
    domain = models.CharField(max_length=20, choices=FraudDomainType.choices, default=FraudDomainType.IT)
    previous_trust_score = models.PositiveSmallIntegerField(null=True, blank=True)
    new_trust_score = models.PositiveSmallIntegerField()
    score_delta = models.IntegerField(help_text="Difference between new and previous score")
    change_reason = models.CharField(max_length=255, default="Resume Re-upload")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Resume Fraud History"
        verbose_name_plural = "Resume Fraud Histories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["seeker_user_id", "domain"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"History User:{self.seeker_user_id} Delta:{self.score_delta} ({self.created_at})"
