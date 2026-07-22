"""Master service orchestrating Resume Trust & Fraud Detection engine scans across IT & Faculty domains."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from apps.core.services.base import BaseService
from apps.resume_trust.models import FraudDomainType
from apps.resume_trust.repositories import ResumeFraudRepository
from apps.resume_trust.services.resume_fraud_builder_and_mappers import (
    ResumeFraudAnalysisBuilder,
    ResumeFraudResultMapper,
    ResumeFraudValidator,
)
from apps.resume_trust.services.resume_fraud_rule_engine import ResumeFraudRuleEngine
from apps.resume_trust.services.resume_trust_score_calculator import ResumeTrustScoreCalculator

logger = logging.getLogger("resume_trust")


class ResumeFraudDetectionService(BaseService):
    """High-level service for executing fraud scans, calculating trust scores, and recording reports."""

    def __init__(
        self,
        repository: Optional[ResumeFraudRepository] = None,
        rule_engine: Optional[ResumeFraudRuleEngine] = None,
        calculator: Optional[ResumeTrustScoreCalculator] = None,
        validator: Optional[ResumeFraudValidator] = None,
        builder: Optional[ResumeFraudAnalysisBuilder] = None,
        mapper: Optional[ResumeFraudResultMapper] = None,
    ):
        self.repository = repository or ResumeFraudRepository()
        self.rule_engine = rule_engine or ResumeFraudRuleEngine()
        self.calculator = calculator or ResumeTrustScoreCalculator()
        self.validator = validator or ResumeFraudValidator()
        self.builder = builder or ResumeFraudAnalysisBuilder()
        self.mapper = mapper or ResumeFraudResultMapper()

    def initiate_analysis(
        self,
        seeker_user_id: int,
        domain: str = FraudDomainType.IT,
        stored_file=None,
        parsed_data: Optional[Dict[str, Any]] = None,
        raw_text: str = "",
        resume_version: int = 1,
    ) -> Dict[str, Any]:
        """Execute trust & fraud scan for an uploaded candidate resume file."""
        start_time = time.perf_counter()
        logger.info(
            "Starting Resume Fraud Detection | Domain: %s | User: %s | File: %s",
            domain,
            seeker_user_id,
            getattr(stored_file, "pk", None),
        )

        # Truncate raw_text to 250,000 chars max to prevent OOM memory issues on large PDF files
        MAX_RAW_TEXT_LEN = 250000
        if raw_text and len(raw_text) > MAX_RAW_TEXT_LEN:
            logger.warning(
                "Truncating raw_text from %d to %d chars for user %s to enforce memory bounds.",
                len(raw_text),
                MAX_RAW_TEXT_LEN,
                seeker_user_id,
            )
            raw_text = raw_text[:MAX_RAW_TEXT_LEN]

        # 1. Mandatory Validation Pipeline: Readability, Non-Resume Detection, Completeness
        from apps.resume_trust.services.resume_validators import (
            ResumeCompletenessValidator,
            ResumeDetectionService,
            ResumeReadabilityValidator,
        )

        readability_val = ResumeReadabilityValidator().validate_stored_file(stored_file, raw_text)
        if not readability_val.is_valid:
            logger.warning(
                "Readability validation failed for user %s: [%s] %s",
                seeker_user_id,
                readability_val.error_code,
                readability_val.error_message,
            )
            analysis = self.repository.create_analysis(
                seeker_user_id=seeker_user_id,
                domain=domain,
                stored_file=stored_file,
                resume_version=resume_version,
            )
            self.repository.mark_failed(analysis, error_message=readability_val.error_message)
            from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
            ResumeFraudReportService.clear_report_cache(seeker_user_id, domain)

            return {
                "id": str(analysis.id),
                "has_analysis": False,
                "status": "FAILED",
                "error_code": readability_val.error_code,
                "error_message": readability_val.error_message,
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "REJECT",
                "warning_count": 0,
                "warnings": [],
                "show_unverified_popup": True,
            }

        detection_val = ResumeDetectionService().detect_resume(raw_text, parsed_data)
        if not detection_val.is_valid:
            logger.warning(
                "Resume classification failed for user %s: [%s] %s",
                seeker_user_id,
                detection_val.error_code,
                detection_val.error_message,
            )
            analysis = self.repository.create_analysis(
                seeker_user_id=seeker_user_id,
                domain=domain,
                stored_file=stored_file,
                resume_version=resume_version,
            )
            self.repository.mark_failed(analysis, error_message=detection_val.error_message)
            from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
            ResumeFraudReportService.clear_report_cache(seeker_user_id, domain)

            return {
                "id": str(analysis.id),
                "has_analysis": False,
                "status": "FAILED",
                "error_code": detection_val.error_code,
                "error_message": detection_val.error_message,
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "REJECT",
                "warning_count": 0,
                "warnings": [],
                "show_unverified_popup": True,
            }

        completeness_val = ResumeCompletenessValidator().validate_completeness(raw_text, parsed_data)
        if not completeness_val.is_valid:
            logger.warning(
                "Completeness validation failed for user %s: [%s] %s",
                seeker_user_id,
                completeness_val.error_code,
                completeness_val.error_message,
            )
            analysis = self.repository.create_analysis(
                seeker_user_id=seeker_user_id,
                domain=domain,
                stored_file=stored_file,
                resume_version=resume_version,
            )
            self.repository.mark_failed(analysis, error_message=completeness_val.error_message)
            from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
            ResumeFraudReportService.clear_report_cache(seeker_user_id, domain)

            return {
                "id": str(analysis.id),
                "has_analysis": False,
                "status": "FAILED",
                "error_code": completeness_val.error_code,
                "error_message": completeness_val.error_message,
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "REJECT",
                "warning_count": 0,
                "warnings": [],
                "show_unverified_popup": True,
            }

        # 2. Fetch previous latest score for history delta calculation
        previous_analysis = self.repository.get_latest_for_user(seeker_user_id, domain=domain)
        previous_score = previous_analysis.trust_score if previous_analysis else None

        # 3. Create initial pending database analysis record
        analysis = self.repository.create_analysis(
            seeker_user_id=seeker_user_id,
            domain=domain,
            stored_file=stored_file,
            resume_version=resume_version,
        )

        try:
            # 4. Evaluate Fraud Rules
            detected_warnings = self.rule_engine.evaluate(
                parsed_data=parsed_data or {}, raw_text=raw_text
            )

            # 5. Save Warnings to Database
            for w in detected_warnings:
                self.repository.add_warning(
                    analysis=analysis,
                    rule_code=w.get("rule_code", "UNKNOWN_RULE"),
                    rule_name=w.get("rule_name", "Unknown Rule"),
                    severity=w.get("severity", "LOW"),
                    title=w.get("title", ""),
                    description=w.get("description", ""),
                    evidence_snippet=w.get("evidence_snippet", ""),
                )

            # 6. Calculate Trust & Risk Scores
            score_results = self.calculator.calculate(detected_warnings)

            duration_ms = int((time.perf_counter() - start_time) * 1000)

            from apps.resume_trust.services.resume_validators import extract_resume_diagnostics
            diagnostics = extract_resume_diagnostics(raw_text=raw_text, parsed_data=parsed_data)

            # 7. Build JSON Analysis Report
            json_report = self.builder.build_report(
                analysis_id=analysis.id,
                domain=domain,
                seeker_user_id=seeker_user_id,
                trust_score=score_results["trust_score"],
                risk_score=score_results["risk_score"],
                risk_level=score_results["risk_level"],
                recommendation=score_results["recommendation"],
                warnings=detected_warnings,
                execution_time_ms=duration_ms,
                category_scores=score_results.get("category_scores"),
                recommendation_message=score_results.get("recommendation_message"),
                diagnostics=diagnostics,
            )

            # 8. Mark Analysis Complete in Database
            completed_analysis = self.repository.mark_completed(
                analysis=analysis,
                trust_score=score_results["trust_score"],
                risk_score=score_results["risk_score"],
                risk_level=score_results["risk_level"],
                warning_count=score_results["warning_count"],
                recommendation=score_results["recommendation"],
                duration_ms=duration_ms,
                json_report=json_report,
            )

            # 9. Log History Record
            self.repository.record_history(
                analysis=completed_analysis,
                previous_score=previous_score,
                change_reason=f"Resume Trust Scan Completed ({domain.upper()})",
            )

            logger.info(
                "Completed Resume Fraud Detection | ID: %s | User: %s | TrustScore: %s | RiskLevel: %s | Duration: %sms",
                completed_analysis.id,
                seeker_user_id,
                completed_analysis.trust_score,
                completed_analysis.risk_level,
                duration_ms,
            )

            # 10. Clear cached trust reports
            from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
            ResumeFraudReportService.clear_report_cache(seeker_user_id, domain)

            return self.mapper.to_dict(completed_analysis)

        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.exception(
                "Error executing Resume Fraud Detection | ID: %s | Duration: %sms | Error: %s",
                analysis.id,
                duration_ms,
                str(exc),
            )
            self.repository.mark_failed(analysis, error_message=str(exc))
            from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
            ResumeFraudReportService.clear_report_cache(seeker_user_id, domain)
            raise exc
