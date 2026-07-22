"""Rule Engine for Resume Trust & Fraud Detection Engine.

Architecture (Open/Closed Principle):
- Add a new rule: subclass BaseResumeRule, register in RULE_REGISTRY.
- This engine never needs to be modified to support new rules.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from apps.resume_trust.services.rules.base_rule import BaseResumeRule
from apps.resume_trust.services.rules.rule_registry import RULE_REGISTRY

logger = logging.getLogger("resume_trust")


class ResumeFraudRuleEngine:
    """Executes all registered fraud detection rules against parsed resume data.

    Usage:
        engine = ResumeFraudRuleEngine()
        warnings = engine.evaluate(parsed_data, raw_text)

    To run a custom/limited rule set:
        engine = ResumeFraudRuleEngine(rules=[ContactValidationRule()])
    """

    def __init__(self, rules: Optional[List[BaseResumeRule]] = None):
        # ponytail: default to global registry; override in tests for isolation
        self._rules: List[BaseResumeRule] = rules if rules is not None else RULE_REGISTRY

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str = "") -> List[Dict[str, Any]]:
        """Execute every registered rule. Return list of warning dicts for failed rules.

        Rules that pass produce no output.
        Rules that fail produce one warning dict each.
        Engine errors on a single rule are isolated — other rules still run.
        """
        warnings: List[Dict[str, Any]] = []

        for rule in self._rules:
            try:
                result = rule.evaluate(parsed_data=parsed_data, raw_text=raw_text)
                if not result.passed:
                    warning = result.to_warning_dict()
                    if warning:
                        warnings.append(warning)
                        logger.debug(
                            "Rule FAILED | %s | Severity: %s | Penalty: %s | Title: %s",
                            rule.RULE_CODE,
                            result.severity,
                            result.score_penalty,
                            result.title,
                        )
                else:
                    logger.debug("Rule PASSED | %s | Confidence: %.2f", rule.RULE_CODE, result.confidence)

            except Exception:
                logger.exception(
                    "Rule engine error — rule %s failed with exception (skipped)",
                    getattr(rule, "RULE_CODE", type(rule).__name__),
                )
                # Isolated failure: continue running remaining rules

        logger.info(
            "Rule engine complete | Rules run: %d | Warnings generated: %d",
            len(self._rules),
            len(warnings),
        )
        return warnings

    @property
    def registered_rule_codes(self) -> List[str]:
        """Return list of rule codes currently registered in this engine instance."""
        return [r.RULE_CODE for r in self._rules]
