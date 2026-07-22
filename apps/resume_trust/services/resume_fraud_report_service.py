"""Service generating user-facing trust dashboard report summaries."""

from __future__ import annotations

from typing import Any, Dict, Optional
from apps.core.services.base import BaseService
from apps.resume_trust.repositories import ResumeFraudRepository
from apps.resume_trust.services.resume_fraud_builder_and_mappers import ResumeFraudResultMapper


from django.core.cache import cache

CACHE_TTL_SECONDS = 300  # 5 minutes cache TTL for trust reports


class ResumeFraudReportService(BaseService):
    """Generates candidate-facing and recruiter-facing trust reports and history timelines."""

    def __init__(self, repository: Optional[ResumeFraudRepository] = None):
        self.repository = repository or ResumeFraudRepository()
        self.mapper = ResumeFraudResultMapper()

    @staticmethod
    def clear_report_cache(seeker_user_id: int, domain: str) -> None:
        """Clear cached trust reports when a new analysis completes."""
        cache.delete(f"trust_candidate_report_{domain}_{seeker_user_id}")
        cache.delete(f"trust_recruiter_report_{domain}_{seeker_user_id}")

    def get_user_latest_report(self, seeker_user_id: int, domain: str) -> Dict[str, Any]:
        """Fetch latest trust analysis report for a candidate with 5-min caching."""
        cache_key = f"trust_candidate_report_{domain}_{seeker_user_id}"
        cached_report = cache.get(cache_key)
        if cached_report is not None:
            return cached_report

        analysis = self.repository.get_latest_for_user(seeker_user_id, domain=domain)
        from apps.resume_trust.services.resume_trust_config import ResumeTrustConfig
        cfg = ResumeTrustConfig.load()

        if not analysis:
            result = {
                "has_analysis": False,
                "status": "NOT_STARTED",
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "PASS",
                "message": "No resume trust analysis completed yet.",
                "popup_trust_threshold": cfg.popup_trust_threshold,
                "show_warning_popup": False,
                "show_unverified_popup": False,
            }
            cache.set(cache_key, result, CACHE_TTL_SECONDS)
            return result

        if analysis.status == "FAILED":
            result = {
                "has_analysis": False,
                "status": "FAILED",
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "REJECT",
                "recommendation_message": analysis.error_message or "Resume could not be analyzed.",
                "message": analysis.error_message or "Resume could not be analyzed.",
                "popup_trust_threshold": cfg.popup_trust_threshold,
                "show_warning_popup": False,
                "show_unverified_popup": True,
                "stored_file_id": str(analysis.stored_file_id) if analysis.stored_file_id else "",
                "resume_version": analysis.resume_version,
            }
            cache.set(cache_key, result, CACHE_TTL_SECONDS)
            return result

        data = self.mapper.to_dict(analysis)
        data["has_analysis"] = True
        data["popup_trust_threshold"] = cfg.popup_trust_threshold
        data["show_warning_popup"] = data.get("trust_score", 100) < cfg.popup_trust_threshold
        data["show_unverified_popup"] = False
        cache.set(cache_key, data, CACHE_TTL_SECONDS)
        return data

    def get_user_trust_history(self, seeker_user_id: int, domain: str, limit: int = 10) -> Dict[str, Any]:
        """Fetch trust score trend history across resume updates."""
        logs = self.repository.get_history_for_user(seeker_user_id, domain=domain, limit=limit)
        history_items = [self.mapper.history_to_dict(item) for item in logs]
        return {
            "seeker_user_id": seeker_user_id,
            "domain": domain,
            "count": len(history_items),
            "history": history_items,
        }

    def get_recruiter_trust_report(self, seeker_user_id: int, domain: str) -> Dict[str, Any]:
        """Fetch recruiter-friendly trust report summary with caching."""
        cache_key = f"trust_recruiter_report_{domain}_{seeker_user_id}"
        cached_report = cache.get(cache_key)
        if cached_report is not None:
            return cached_report

        analysis = self.repository.get_latest_for_user(seeker_user_id, domain=domain)
        if not analysis:
            result = {
                "has_analysis": False,
                "status": "NOT_STARTED",
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "PASS",
                "recommendation_message": "No automated trust scan has been performed yet.",
                "analysis_date": "—",
                "resume_version": 1,
                "warning_count": 0,
                "warnings": [],
            }
            cache.set(cache_key, result, CACHE_TTL_SECONDS)
            return result

        if analysis.status == "FAILED":
            from django.utils import timezone
            analysis_date = (
                timezone.localtime(analysis.created_at).strftime("%b %d, %Y")
                if analysis.created_at
                else "—"
            )
            result = {
                "has_analysis": False,
                "status": "FAILED",
                "trust_score": None,
                "risk_level": "NOT_EVALUATED",
                "recommendation": "REJECT",
                "recommendation_message": analysis.error_message or "Resume could not be analyzed.",
                "analysis_date": analysis_date,
                "resume_version": analysis.resume_version,
                "warning_count": 0,
                "warnings": [],
            }
            cache.set(cache_key, result, CACHE_TTL_SECONDS)
            return result

        report = analysis.analysis_report or {}
        raw_warnings = report.get("warnings") or []

        # Sanitize internal engine details — keep only recruiter-relevant fields
        recruiter_warnings = []
        for w in raw_warnings:
            recruiter_warnings.append({
                "category": w.get("category") or "General",
                "title": w.get("title") or "Verification Signal",
                "severity": w.get("severity") or "LOW",
                "description": w.get("description") or "",
                "recommendation": w.get("recommendation") or "Verify during candidate screening.",
            })

        from django.utils import timezone
        analysis_date = (
            timezone.localtime(analysis.created_at).strftime("%b %d, %Y")
            if analysis.created_at
            else "—"
        )

        result = {
            "has_analysis": True,
            "analysis_id": str(analysis.id),
            "trust_score": analysis.trust_score,
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level,
            "recommendation": analysis.recommendation,
            "recommendation_message": report.get("recommendation_message")
            or report.get("ai_explanation")
            or "Resume verified.",
            "analysis_date": analysis_date,
            "resume_version": analysis.resume_version,
            "warning_count": analysis.warning_count,
            "warnings": recruiter_warnings,
            "status": analysis.status,
        }
        cache.set(cache_key, result, CACHE_TTL_SECONDS)
        return result
