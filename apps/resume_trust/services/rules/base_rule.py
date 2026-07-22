"""Abstract base class for Resume Fraud Detection rules.

Open/Closed Principle: Add new rules by subclassing BaseResumeRule.
Never modify this file or the engine to add new rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuleResult:
    """Standardised output from a single fraud detection rule."""
    rule_code: str
    rule_name: str
    passed: bool
    score_penalty: int          # 0-100 additive penalty applied if not passed
    confidence: float           # 0.0-1.0
    severity: str               # LOW | MEDIUM | HIGH | CRITICAL
    title: str = ""
    description: str = ""
    evidence_snippet: str = ""
    recommendation: str = ""    # Human-readable recommendation string
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_warning_dict(self) -> Optional[Dict[str, Any]]:
        """Convert to warning dict consumed by ResumeFraudDetectionService."""
        if self.passed:
            return None
        return {
            "rule_code": self.rule_code,
            "rule_name": self.rule_name,
            "severity": self.severity,
            "weight": self.score_penalty,
            "title": self.title,
            "description": self.description,
            "evidence_snippet": self.evidence_snippet,
            "confidence": self.confidence,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


class BaseResumeRule(ABC):
    """Abstract base for all resume fraud detection rules.

    Subclass this. Override evaluate(). Register in RULE_REGISTRY.
    Never touch the engine to add a new rule — that is the entire point.
    """

    # Subclasses set these as class-level constants
    RULE_CODE: str = ""
    RULE_NAME: str = ""
    CATEGORY: str = ""
    DEFAULT_WEIGHT: int = 10    # Default penalty applied on failure

    @abstractmethod
    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        """Run the rule against extracted resume data.

        Args:
            parsed_data: Structured extraction dict from AI/parser output.
            raw_text: Raw resume text (for pattern / regex analysis).

        Returns:
            RuleResult instance.
        """
        ...

    def _pass(self, confidence: float = 1.0, metadata: Dict[str, Any] = None) -> RuleResult:
        """Helper to create a passing result."""
        return RuleResult(
            rule_code=self.RULE_CODE,
            rule_name=self.RULE_NAME,
            passed=True,
            score_penalty=0,
            confidence=confidence,
            severity="LOW",
            metadata=metadata or {},
        )

    def _fail(
        self,
        title: str,
        description: str,
        severity: str,
        penalty: int = None,
        evidence: str = "",
        confidence: float = 0.8,
        recommendation: str = "",
        metadata: Dict[str, Any] = None,
    ) -> RuleResult:
        """Helper to create a failing result."""
        return RuleResult(
            rule_code=self.RULE_CODE,
            rule_name=self.RULE_NAME,
            passed=False,
            score_penalty=penalty if penalty is not None else self.DEFAULT_WEIGHT,
            confidence=confidence,
            severity=severity,
            title=title,
            description=description,
            evidence_snippet=evidence,
            recommendation=recommendation,
            metadata=metadata or {},
        )
