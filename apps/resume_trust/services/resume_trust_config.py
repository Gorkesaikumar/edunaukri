"""Typed configuration loader for the Resume Trust & Fraud Detection Engine.

Reads from Django settings RESUME_TRUST_ENGINE dict.
Never hardcodes threshold values — always delegates to settings.

Usage:
    cfg = ResumeTrustConfig.load()
    cfg.severity_weights["HIGH"]          # → 30
    cfg.category_weight("Timeline")       # → 1.5
    cfg.risk_threshold("CRITICAL")        # → 70
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from django.conf import settings


@dataclass(frozen=True)
class ResumeTrustConfig:
    severity_weights: Dict[str, int]
    category_weights: Dict[str, float]
    risk_thresholds: Dict[str, int]         # CRITICAL / HIGH / MEDIUM → int threshold
    base_confidence_no_warnings: float
    base_confidence_with_warnings: float
    confidence_penalty_per_warning: float
    min_confidence: float
    rule_weight_overrides: Dict[str, int]
    recommendation_messages: Dict[str, str]
    popup_trust_threshold: int = 70

    # ── Convenience accessors ───────────────────────────────────────────────

    def severity_weight(self, severity: str) -> int:
        return self.severity_weights.get(severity.upper(), self.severity_weights.get("LOW", 5))

    def category_weight(self, category: str) -> float:
        return self.category_weights.get(category, 1.0)

    def risk_threshold(self, level: str) -> int:
        return self.risk_thresholds.get(level.upper(), 0)

    def rule_override(self, rule_code: str) -> int | None:
        return self.rule_weight_overrides.get(rule_code)

    def recommendation_message(self, recommendation: str) -> str:
        return self.recommendation_messages.get(
            recommendation,
            "Please review this resume carefully.",
        )

    # ── Factory ─────────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> "ResumeTrustConfig":
        """Load configuration from Django settings.RESUME_TRUST_ENGINE."""
        raw: Dict[str, Any] = getattr(settings, "RESUME_TRUST_ENGINE", {})
        return cls(
            severity_weights=raw.get("SEVERITY_WEIGHTS", {
                "LOW": 5, "MEDIUM": 15, "HIGH": 30, "CRITICAL": 50,
            }),
            category_weights=raw.get("CATEGORY_WEIGHTS", {}),
            risk_thresholds=raw.get("RISK_THRESHOLDS", {
                "CRITICAL": 70, "HIGH": 40, "MEDIUM": 15,
            }),
            base_confidence_no_warnings=raw.get("BASE_CONFIDENCE_NO_WARNINGS", 0.95),
            base_confidence_with_warnings=raw.get("BASE_CONFIDENCE_WITH_WARNINGS", 1.00),
            confidence_penalty_per_warning=raw.get("CONFIDENCE_PENALTY_PER_WARNING", 0.02),
            min_confidence=raw.get("MIN_CONFIDENCE", 0.40),
            rule_weight_overrides=raw.get("RULE_WEIGHT_OVERRIDES", {}),
            recommendation_messages=raw.get("RECOMMENDATION_MESSAGES", {}),
            popup_trust_threshold=raw.get("POPUP_TRUST_THRESHOLD", 70),
        )
