"""Repository layer for Resume Trust & Fraud Detection Engine."""

from __future__ import annotations

from typing import Optional
from django.db import transaction

from apps.core.repositories.crud import FilteringRepository
from apps.resume_trust.models import (
    AnalysisRecommendation,
    AnalysisStatus,
    FraudDomainType,
    ResumeFraudAnalysis,
    ResumeFraudHistory,
    ResumeFraudWarning,
    RiskLevel,
    SeverityLevel,
)


class ResumeFraudRepository(FilteringRepository):
    """Repository handling database operations for fraud analyses, warnings, and history."""

    def __init__(self, model=ResumeFraudAnalysis):
        self.model = model

    @transaction.atomic
    def create_analysis(
        self,
        seeker_user_id,
        domain: str = FraudDomainType.IT,
        stored_file=None,
        resume_version: int = 1,
    ) -> ResumeFraudAnalysis:
        """Create a new pending fraud analysis record."""
        return ResumeFraudAnalysis.objects.create(
            seeker_user_id=str(seeker_user_id),
            domain=domain,
            stored_file=stored_file,
            resume_version=resume_version,
            status=AnalysisStatus.PENDING,
        )

    @transaction.atomic
    def add_warning(
        self,
        analysis: ResumeFraudAnalysis,
        rule_code: str,
        rule_name: str,
        severity: str = SeverityLevel.LOW,
        title: str = "",
        description: str = "",
        evidence_snippet: str = "",
    ) -> ResumeFraudWarning:
        """Attach a fraud warning to an analysis record."""
        warning = ResumeFraudWarning.objects.create(
            fraud_analysis=analysis,
            rule_code=rule_code,
            rule_name=rule_name,
            severity=severity,
            title=title or rule_name,
            description=description,
            evidence_snippet=evidence_snippet,
        )
        analysis.warning_count = analysis.warnings.count()
        analysis.save(update_fields=["warning_count", "updated_at"])
        return warning

    @transaction.atomic
    def record_history(
        self,
        analysis: ResumeFraudAnalysis,
        previous_score: Optional[int] = None,
        change_reason: str = "Resume Analysis Completed",
    ) -> ResumeFraudHistory:
        """Log score changes into audit history."""
        delta = (analysis.trust_score - previous_score) if previous_score is not None else 0
        return ResumeFraudHistory.objects.create(
            fraud_analysis=analysis,
            seeker_user_id=str(analysis.seeker_user_id),
            domain=analysis.domain,
            previous_trust_score=previous_score,
            new_trust_score=analysis.trust_score,
            score_delta=delta,
            change_reason=change_reason,
        )

    def get_latest_for_user(
        self, seeker_user_id, domain: str = FraudDomainType.IT, include_failed: bool = True
    ) -> Optional[ResumeFraudAnalysis]:
        """Fetch the most recent analysis for a candidate."""
        qs = ResumeFraudAnalysis.objects.filter(
            seeker_user_id=str(seeker_user_id),
            domain=domain,
        )
        if not include_failed:
            qs = qs.filter(status=AnalysisStatus.SUCCESS)
        else:
            qs = qs.filter(status__in=[AnalysisStatus.SUCCESS, AnalysisStatus.FAILED])
        return qs.order_by("-created_at").first()

    def get_history_for_user(
        self, seeker_user_id, domain: str = FraudDomainType.IT, limit: int = 10
    ):
        """Fetch historical score trend logs for a candidate."""
        return ResumeFraudHistory.objects.filter(
            seeker_user_id=str(seeker_user_id), domain=domain
        ).order_by("-created_at")[:limit]

    @transaction.atomic
    def mark_completed(
        self,
        analysis: ResumeFraudAnalysis,
        trust_score: int,
        risk_score: int,
        risk_level: str,
        warning_count: int,
        recommendation: str,
        duration_ms: int,
        json_report: dict,
    ) -> ResumeFraudAnalysis:
        """Mark an analysis completed with final calculated scores and report."""
        analysis.trust_score = max(0, min(100, trust_score))
        analysis.risk_score = max(0, min(100, risk_score))
        analysis.risk_level = risk_level
        analysis.warning_count = warning_count
        analysis.recommendation = recommendation
        analysis.analysis_duration_ms = duration_ms
        analysis.json_analysis_report = json_report
        analysis.status = AnalysisStatus.SUCCESS
        analysis.save(
            update_fields=[
                "trust_score",
                "risk_score",
                "risk_level",
                "warning_count",
                "recommendation",
                "analysis_duration_ms",
                "json_analysis_report",
                "status",
                "updated_at",
            ]
        )
        return analysis

    @transaction.atomic
    def mark_failed(
        self, analysis: ResumeFraudAnalysis, error_message: str
    ) -> ResumeFraudAnalysis:
        """Mark analysis failed with error details."""
        analysis.status = AnalysisStatus.FAILED
        analysis.error_message = error_message
        analysis.save(update_fields=["status", "error_message", "updated_at"])
        return analysis
