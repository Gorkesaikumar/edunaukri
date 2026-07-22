"""Builder, Validator, and Mapper helpers for Resume Trust & Fraud Detection Engine."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.resume_trust.models import ResumeFraudAnalysis, ResumeFraudHistory


class ResumeFraudValidator:
    """Validates resume file eligibility for trust & fraud analysis."""

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc"}

    def validate(self, stored_file) -> None:
        """Ensure file object is valid and supported."""
        if not stored_file:
            raise ValidationException("Resume file is required for fraud analysis.")

        filename = getattr(stored_file, "original_filename", "") or getattr(stored_file, "file_name", "")
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValidationException(f"Unsupported file format '{ext}'. Must be PDF or DOCX.")


class ResumeFraudAnalysisBuilder:
    """Structures full JSON analysis report outputs."""

    def build_report(
        self,
        analysis_id: str,
        domain: str,
        seeker_user_id: int,
        trust_score: int,
        risk_score: int,
        risk_level: str,
        recommendation: str,
        warnings: List[Dict[str, Any]],
        execution_time_ms: int,
        ai_explanation: Optional[str] = None,
        category_scores: Optional[Dict[str, Any]] = None,
        recommendation_message: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build standardized JSON report structure with diagnostics explainability."""
        diag = diagnostics or {}
        return {
            "analysis_id": str(analysis_id),
            "domain": domain,
            "seeker_user_id": str(seeker_user_id),
            "trust_score": trust_score,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "recommendation_message": recommendation_message or self._default_message(recommendation),
            "warning_count": len(warnings),
            "warnings": warnings,
            "category_scores": category_scores or {},
            "execution_time_ms": execution_time_ms,
            "ai_explanation": ai_explanation or self._default_explanation(trust_score, risk_level),
            "reason": ai_explanation or self._default_explanation(trust_score, risk_level),
            "passed_checks": diag.get("passed_checks", []),
            "failed_checks": diag.get("failed_checks", []),
            "detected_sections": diag.get("detected_sections", []),
            "missing_sections": diag.get("missing_sections", []),
            "recommendations": diag.get("recommendations", []),
        }

    def _default_message(self, recommendation: str) -> str:
        messages = {
            "PASS": "Resume passed all automated checks. Candidate may proceed to the next stage.",
            "FLAG_FOR_REVIEW": (
                "Resume has been flagged for manual review. "
                "Verify the highlighted sections with the candidate before proceeding."
            ),
            "REJECT": (
                "Resume failed critical trust checks. "
                "This candidate should not proceed without thorough background verification."
            ),
        }
        return messages.get(recommendation, "Please review this resume carefully.")

    def _default_explanation(self, trust_score: int, risk_level: str) -> str:
        if risk_level == "LOW":
            return f"Resume verified successfully with a high trust score of {trust_score}/100. No major risk factors identified."
        elif risk_level == "MEDIUM":
            return f"Resume has moderate trust score ({trust_score}/100). Flagged for minor inconsistencies or missing optional sections."
        else:
            return f"Resume received low trust score ({trust_score}/100) and elevated risk classification ({risk_level}). Manual review recommended."


class ResumeFraudResultMapper:
    """Maps database entities into API response DTO dictionaries."""

    def to_dict(self, analysis: ResumeFraudAnalysis) -> Dict[str, Any]:
        """Convert ResumeFraudAnalysis model instance to JSON response dictionary."""
        if not analysis:
            return {}

        report = analysis.json_analysis_report or {}
        warnings_list = [
            {
                "id": str(w.id),
                "rule_code": w.rule_code,
                "rule_name": w.rule_name,
                "severity": w.severity,
                "title": w.title,
                "description": w.description,
                "evidence_snippet": w.evidence_snippet,
            }
            for w in analysis.warnings.all()
        ] if hasattr(analysis, "warnings") else report.get("warnings", [])

        return {
            "id": str(analysis.id),
            "domain": analysis.domain,
            "seeker_user_id": analysis.seeker_user_id,
            "stored_file_id": str(analysis.stored_file_id) if analysis.stored_file_id else None,
            "resume_version": analysis.resume_version,
            "trust_score": analysis.trust_score,
            "risk_score": analysis.risk_score,
            "confidence_score": float(analysis.confidence_score),
            "risk_level": analysis.risk_level,
            "warning_count": analysis.warning_count,
            "recommendation": analysis.recommendation,
            "recommendation_message": report.get("recommendation_message", ""),
            "category_scores": report.get("category_scores", {}),
            "status": analysis.status,
            "analysis_duration_ms": analysis.analysis_duration_ms,
            "ai_explanation": report.get("ai_explanation", ""),
            "reason": report.get("reason") or report.get("ai_explanation", ""),
            "passed_checks": report.get("passed_checks", []),
            "failed_checks": report.get("failed_checks", []),
            "detected_sections": report.get("detected_sections", []),
            "missing_sections": report.get("missing_sections", []),
            "recommendations": report.get("recommendations", []),
            "warnings": warnings_list,
            "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
        }

    def history_to_dict(self, history_item: ResumeFraudHistory) -> Dict[str, Any]:
        """Convert ResumeFraudHistory instance to dictionary."""
        return {
            "id": str(history_item.id),
            "analysis_id": str(history_item.fraud_analysis_id),
            "seeker_user_id": history_item.seeker_user_id,
            "domain": history_item.domain,
            "previous_trust_score": history_item.previous_trust_score,
            "new_trust_score": history_item.new_trust_score,
            "score_delta": history_item.score_delta,
            "change_reason": history_item.change_reason,
            "created_at": history_item.created_at.isoformat() if history_item.created_at else None,
        }
