"""Unit tests for the production-grade ResumeTrustScoreCalculator."""

from __future__ import annotations

import pytest

from apps.resume_trust.models import AnalysisRecommendation, RiskLevel
from apps.resume_trust.services.resume_trust_config import ResumeTrustConfig
from apps.resume_trust.services.resume_trust_score_calculator import (
    ResumeTrustScoreCalculator,
    TrustScoreResult,
)


# ── Shared test config (avoids touching Django settings) ─────────────────────

def make_config(**overrides) -> ResumeTrustConfig:
    defaults = dict(
        severity_weights={"LOW": 5, "MEDIUM": 15, "HIGH": 30, "CRITICAL": 50},
        category_weights={
            "Timeline":          1.5,
            "Education":         1.5,
            "Skills":            1.0,
            "Content Integrity": 1.0,
            "Contact":           1.2,
            "Completeness":      0.8,
            "Employment":        1.3,
            "Certifications":    1.0,
        },
        risk_thresholds={"CRITICAL": 70, "HIGH": 40, "MEDIUM": 15},
        base_confidence_no_warnings=0.95,
        base_confidence_with_warnings=1.00,
        confidence_penalty_per_warning=0.02,
        min_confidence=0.40,
        rule_weight_overrides={},
        recommendation_messages={
            "PASS": "Pass message",
            "FLAG_FOR_REVIEW": "Review message",
            "REJECT": "Reject message",
        },
    )
    defaults.update(overrides)
    return ResumeTrustConfig(**defaults)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestResumeTrustConfig:
    def test_load_from_settings_succeeds(self):
        # Should not raise — Django settings has RESUME_TRUST_ENGINE block
        cfg = ResumeTrustConfig.load()
        assert cfg.severity_weight("HIGH") == 30
        assert cfg.category_weight("Timeline") == 1.5
        assert cfg.risk_threshold("CRITICAL") == 70

    def test_category_weight_defaults_to_one_for_unknown(self):
        cfg = make_config()
        assert cfg.category_weight("UnknownCategory") == 1.0

    def test_rule_override_returns_none_when_absent(self):
        cfg = make_config()
        assert cfg.rule_override("TIMELINE_001") is None

    def test_rule_override_returns_value_when_present(self):
        cfg = make_config(rule_weight_overrides={"TIMELINE_001": 99})
        assert cfg.rule_override("TIMELINE_001") == 99

    def test_recommendation_message_fallback(self):
        cfg = make_config(recommendation_messages={})
        msg = cfg.recommendation_message("PASS")
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestResumeTrustScoreCalculatorCleanResume:
    def setup_method(self):
        self.cfg = make_config()
        self.calc = ResumeTrustScoreCalculator(config=self.cfg)

    def test_no_warnings_returns_perfect_score(self):
        result = self.calc.calculate_full([])
        assert result.trust_score == 100
        assert result.risk_score == 0
        assert result.risk_level == RiskLevel.LOW
        assert result.recommendation == AnalysisRecommendation.PASS
        assert result.warning_count == 0
        assert result.confidence_score == 0.95  # base_confidence_no_warnings

    def test_no_warnings_produces_empty_category_scores(self):
        result = self.calc.calculate_full([])
        assert result.category_scores == {}

    def test_no_warnings_has_pass_recommendation_message(self):
        result = self.calc.calculate_full([])
        assert "Pass message" in result.recommendation_message


class TestResumeTrustScoreCalculatorWeighting:
    def setup_method(self):
        self.cfg = make_config()
        self.calc = ResumeTrustScoreCalculator(config=self.cfg)

    def test_single_medium_contact_warning(self):
        """Contact weight=1.2, MEDIUM penalty=15 → weighted=18 → risk=18 → MEDIUM."""
        warnings = [{
            "rule_code": "CONTACT_001",
            "rule_name": "Contact Validation",
            "category": "Contact",
            "severity": "MEDIUM",
            "weight": 15,
        }]
        result = self.calc.calculate_full(warnings)
        assert result.risk_score == 18         # 15 × 1.2
        assert result.trust_score == 82
        assert result.risk_level == RiskLevel.MEDIUM
        assert "Contact" in result.category_scores
        assert result.category_scores["Contact"].weighted_penalty == 18.0

    def test_single_high_timeline_warning(self):
        """Timeline weight=1.5, HIGH penalty=30 → weighted=45 → risk=45 → HIGH."""
        warnings = [{
            "rule_code": "TIMELINE_001",
            "rule_name": "Timeline Validation",
            "category": "Timeline",
            "severity": "HIGH",
            "weight": 30,
        }]
        result = self.calc.calculate_full(warnings)
        assert result.risk_score == 45         # 30 × 1.5
        assert result.trust_score == 55
        assert result.risk_level == RiskLevel.HIGH
        assert result.recommendation == AnalysisRecommendation.FLAG_FOR_REVIEW

    def test_critical_combined_warnings_trigger_reject(self):
        """Multiple CRITICAL-weighted warnings → risk > 70 → REJECT."""
        warnings = [
            {"rule_code": "TIMELINE_001", "category": "Timeline",  "severity": "CRITICAL", "weight": 50},
            {"rule_code": "EDUCATION_001","category": "Education", "severity": "CRITICAL", "weight": 50},
        ]
        result = self.calc.calculate_full(warnings)
        # (50×1.5) + (50×1.5) = 75 + 75 = 150 → capped at 100
        assert result.risk_score == 100
        assert result.trust_score == 0
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.recommendation == AnalysisRecommendation.REJECT

    def test_completeness_reduced_weight(self):
        """Completeness multiplier=0.8 reduces impact of missing sections."""
        warnings = [{
            "rule_code": "COMPLETENESS_001",
            "category": "Completeness",
            "severity": "HIGH",
            "weight": 30,
        }]
        result = self.calc.calculate_full(warnings)
        # 30 × 0.8 = 24 → MEDIUM (> 15, ≤ 40)
        assert result.risk_score == 24
        assert result.risk_level == RiskLevel.MEDIUM

    def test_category_scores_contain_all_triggered_categories(self):
        warnings = [
            {"rule_code": "CONTACT_001",  "category": "Contact",   "severity": "LOW",    "weight": 5},
            {"rule_code": "SKILL_001",    "category": "Skills",    "severity": "MEDIUM", "weight": 15},
            {"rule_code": "KEYWORD_001",  "category": "Content Integrity", "severity": "LOW", "weight": 5},
        ]
        result = self.calc.calculate_full(warnings)
        assert set(result.category_scores.keys()) == {"Contact", "Skills", "Content Integrity"}


class TestResumeTrustScoreCalculatorRuleOverrides:
    def test_rule_weight_override_applied(self):
        cfg = make_config(rule_weight_overrides={"TIMELINE_001": 11})
        calc = ResumeTrustScoreCalculator(config=cfg)
        warnings = [{"rule_code": "TIMELINE_001", "category": "Timeline", "severity": "CRITICAL", "weight": 50}]
        result = calc.calculate_full(warnings)
        # Override replaces 50 with 11 → 11 × 1.5 = 16.5 → int(round(16.5)) = 16 (banker's rounding)
        # 16 > 15 → MEDIUM
        assert result.risk_score == 16
        assert result.risk_level == RiskLevel.MEDIUM

    def test_no_overrides_uses_warning_weight_as_is(self):
        cfg = make_config(rule_weight_overrides={})
        calc = ResumeTrustScoreCalculator(config=cfg)
        warnings = [{"rule_code": "TIMELINE_001", "category": "Timeline", "severity": "HIGH", "weight": 30}]
        result = calc.calculate_full(warnings)
        assert result.risk_score == 45  # 30 × 1.5


class TestResumeTrustScoreCalculatorConfidence:
    def setup_method(self):
        self.calc = ResumeTrustScoreCalculator(config=make_config())

    def test_confidence_decreases_with_more_warnings(self):
        few_warnings = [{"rule_code": "X", "category": "Contact", "severity": "LOW", "weight": 1}]
        many_warnings = few_warnings * 15

        r_few = self.calc.calculate_full(few_warnings)
        r_many = self.calc.calculate_full(many_warnings)
        assert r_few.confidence_score > r_many.confidence_score

    def test_confidence_never_below_minimum(self):
        # 30 warnings × 0.02 penalty = 0.60 reduction from 1.00 → floor at 0.40
        warnings = [{"rule_code": "X", "category": "Contact", "severity": "LOW", "weight": 1}] * 30
        result = self.calc.calculate_full(warnings)
        assert result.confidence_score >= 0.40

    def test_perfect_resume_has_base_no_warning_confidence(self):
        result = self.calc.calculate_full([])
        assert result.confidence_score == 0.95


class TestResumeTrustScoreCalculatorCategoryInference:
    def setup_method(self):
        self.calc = ResumeTrustScoreCalculator(config=make_config())

    def test_category_inferred_from_rule_code_when_missing(self):
        """If 'category' field is missing, it is inferred from rule_code prefix."""
        warnings = [{"rule_code": "TIMELINE_001", "severity": "HIGH", "weight": 30}]
        result = self.calc.calculate_full(warnings)
        assert "Timeline" in result.category_scores

    def test_unknown_rule_code_falls_to_general_category(self):
        warnings = [{"rule_code": "CUSTOM_XYZ_999", "severity": "LOW", "weight": 5}]
        result = self.calc.calculate_full(warnings)
        assert "General" in result.category_scores


class TestResumeTrustScoreCalculatorBackwardCompat:
    """Verify the calculate() dict-returning method still works as before."""

    def setup_method(self):
        self.calc = ResumeTrustScoreCalculator(config=make_config())

    def test_calculate_returns_dict_with_required_keys(self):
        result = self.calc.calculate([])
        required = {"trust_score", "risk_score", "risk_level", "recommendation",
                    "confidence_score", "warning_count"}
        assert required <= set(result.keys())

    def test_calculate_includes_new_keys(self):
        result = self.calc.calculate([])
        assert "category_scores" in result
        assert "recommendation_message" in result

    def test_calculate_trust_score_is_integer(self):
        result = self.calc.calculate([])
        assert isinstance(result["trust_score"], int)
        assert isinstance(result["risk_score"], int)
