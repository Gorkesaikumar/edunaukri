"""Production-grade Trust Score Calculator for the Resume Trust & Fraud Detection Engine.

Calculates:
  - Overall Trust Score (0–100) — weighted, config-driven
  - Overall Risk Score  (0–100)
  - Confidence Score    (0.0–1.0)
  - Risk Level          (LOW / MEDIUM / HIGH / CRITICAL)
  - Per-category scores — one sub-score per rule category
  - Recommendation      (PASS / FLAG_FOR_REVIEW / REJECT) + human-readable message
  - Structured warnings list grouped by category

All thresholds and weights are read from Django settings.RESUME_TRUST_ENGINE.
No numeric thresholds are hardcoded anywhere in this module.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from apps.resume_trust.models import AnalysisRecommendation, RiskLevel
from apps.resume_trust.services.resume_trust_config import ResumeTrustConfig

logger = logging.getLogger("resume_trust")


# ─────────────────────────────────────────────────────────────────────────────
# Output dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CategoryScore:
    """Score breakdown for a single rule category."""
    category: str
    raw_penalty: int           # Sum of raw penalties from rules in this category
    weighted_penalty: float    # raw_penalty × category multiplier
    warning_count: int
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category":         self.category,
            "raw_penalty":      self.raw_penalty,
            "weighted_penalty": round(self.weighted_penalty, 2),
            "warning_count":    self.warning_count,
        }


@dataclass
class TrustScoreResult:
    """Full calculation result returned by ResumeTrustScoreCalculator.calculate()."""
    trust_score: int
    risk_score: int
    confidence_score: float
    risk_level: str
    recommendation: str
    recommendation_message: str
    warning_count: int
    category_scores: Dict[str, CategoryScore]
    warnings_by_category: Dict[str, List[Dict[str, Any]]]
    all_warnings: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trust_score":            self.trust_score,
            "risk_score":             self.risk_score,
            "confidence_score":       round(self.confidence_score, 4),
            "risk_level":             self.risk_level,
            "recommendation":         self.recommendation,
            "recommendation_message": self.recommendation_message,
            "warning_count":          self.warning_count,
            "category_scores": {
                cat: cs.to_dict()
                for cat, cs in self.category_scores.items()
            },
            "warnings_by_category": self.warnings_by_category,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Calculator
# ─────────────────────────────────────────────────────────────────────────────

class ResumeTrustScoreCalculator:
    """Weighted, config-driven trust and risk score calculator.

    All thresholds and category multipliers come from settings.RESUME_TRUST_ENGINE.
    Pass a custom ResumeTrustConfig in tests to avoid touching Django settings.
    """

    def __init__(self, config: Optional[ResumeTrustConfig] = None):
        # ponytail: lazy-load config by default; inject in tests for isolation
        self._config: Optional[ResumeTrustConfig] = config

    @property
    def cfg(self) -> ResumeTrustConfig:
        if self._config is None:
            self._config = ResumeTrustConfig.load()
        return self._config

    # ── Public API ──────────────────────────────────────────────────────────

    def calculate(self, warnings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Backward-compatible entry point — returns a plain dict.

        Internally delegates to calculate_full() which returns TrustScoreResult.
        Preserves the existing dict contract consumed by ResumeFraudDetectionService.
        """
        result = self.calculate_full(warnings)
        d = result.to_dict()
        # Keep existing keys the caller already reads
        d["warning_count"] = result.warning_count
        return d

    def calculate_full(self, warnings: List[Dict[str, Any]]) -> TrustScoreResult:
        """Full weighted calculation returning a structured TrustScoreResult."""
        cfg = self.cfg

        # ── 1. Apply rule-level weight overrides from config ─────────────────
        effective_warnings = self._apply_overrides(warnings, cfg)

        # ── 2. Group warnings by category ────────────────────────────────────
        by_category: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for w in effective_warnings:
            cat = w.get("category") or self._infer_category(w.get("rule_code", ""))
            by_category[cat].append(w)

        # ── 3. Compute per-category weighted penalties ────────────────────────
        category_scores: Dict[str, CategoryScore] = {}
        total_weighted_penalty: float = 0.0

        for cat, cat_warnings in by_category.items():
            raw_penalty = sum(
                self._effective_penalty(w, cfg) for w in cat_warnings
            )
            multiplier = cfg.category_weight(cat)
            weighted = raw_penalty * multiplier
            total_weighted_penalty += weighted
            category_scores[cat] = CategoryScore(
                category=cat,
                raw_penalty=raw_penalty,
                weighted_penalty=weighted,
                warning_count=len(cat_warnings),
                warnings=cat_warnings,
            )

        # ── 4. Normalise to 0–100 ─────────────────────────────────────────────
        risk_score = int(min(100, max(0, round(total_weighted_penalty))))
        trust_score = max(0, 100 - risk_score)

        # ── 5. Classify risk level ────────────────────────────────────────────
        risk_level, recommendation = self._classify(risk_score, cfg)

        # ── 6. Compute confidence ─────────────────────────────────────────────
        confidence = self._compute_confidence(effective_warnings, cfg)

        # ── 7. Resolve recommendation message ────────────────────────────────
        rec_message = cfg.recommendation_message(recommendation)

        result = TrustScoreResult(
            trust_score=trust_score,
            risk_score=risk_score,
            confidence_score=confidence,
            risk_level=risk_level,
            recommendation=recommendation,
            recommendation_message=rec_message,
            warning_count=len(effective_warnings),
            category_scores=category_scores,
            warnings_by_category=dict(by_category),
            all_warnings=effective_warnings,
        )

        logger.debug(
            "TrustScore=%d | RiskScore=%d | Confidence=%.2f | Level=%s | Categories=%s",
            trust_score, risk_score, confidence, risk_level,
            {c: round(cs.weighted_penalty, 1) for c, cs in category_scores.items()},
        )
        return result

    # ── Private helpers ──────────────────────────────────────────────────────

    def _apply_overrides(
        self, warnings: List[Dict[str, Any]], cfg: ResumeTrustConfig
    ) -> List[Dict[str, Any]]:
        """Return a new warnings list with rule-level weight overrides applied."""
        if not cfg.rule_weight_overrides:
            return warnings
        result = []
        for w in warnings:
            override = cfg.rule_override(w.get("rule_code", ""))
            if override is not None:
                w = {**w, "weight": override}
            result.append(w)
        return result

    def _effective_penalty(self, warning: Dict[str, Any], cfg: ResumeTrustConfig) -> int:
        """Resolve the effective penalty for one warning dict."""
        if "weight" in warning and warning["weight"] is not None:
            return int(warning["weight"])
        sev = str(warning.get("severity", "LOW")).upper()
        return cfg.severity_weight(sev)

    @staticmethod
    def _classify(risk_score: int, cfg: ResumeTrustConfig):
        """Map risk_score to (risk_level, recommendation) using config thresholds."""
        thresholds = cfg.risk_thresholds
        if risk_score > thresholds.get("CRITICAL", 70):
            return RiskLevel.CRITICAL, AnalysisRecommendation.REJECT
        if risk_score > thresholds.get("HIGH", 40):
            return RiskLevel.HIGH, AnalysisRecommendation.FLAG_FOR_REVIEW
        if risk_score > thresholds.get("MEDIUM", 15):
            return RiskLevel.MEDIUM, AnalysisRecommendation.FLAG_FOR_REVIEW
        return RiskLevel.LOW, AnalysisRecommendation.PASS

    @staticmethod
    def _compute_confidence(
        warnings: List[Dict[str, Any]], cfg: ResumeTrustConfig
    ) -> float:
        """Compute confidence score — decreases as unresolved warnings pile up."""
        if not warnings:
            return cfg.base_confidence_no_warnings
        base = cfg.base_confidence_with_warnings
        penalty = cfg.confidence_penalty_per_warning * len(warnings)
        return max(cfg.min_confidence, round(base - penalty, 4))

    @staticmethod
    def _infer_category(rule_code: str) -> str:
        """Fall back category from rule_code prefix if warning lacks a category field."""
        prefix_map = {
            "TIMELINE": "Timeline",
            "EDUCATION": "Education",
            "SKILL": "Skills",
            "KEYWORD": "Content Integrity",
            "CONTACT": "Contact",
            "COMPLETENESS": "Completeness",
            "COMPANY": "Employment",
            "CERT": "Certifications",
        }
        upper = rule_code.upper()
        for prefix, cat in prefix_map.items():
            if upper.startswith(prefix):
                return cat
        return "General"
