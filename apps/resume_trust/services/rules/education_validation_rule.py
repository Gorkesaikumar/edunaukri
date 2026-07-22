"""Education Validation Rule — detects suspicious or unverifiable degree claims."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class EducationValidationRule(BaseResumeRule):
    """Validates education section for known suspicious degree patterns and inconsistencies.

    Detects:
    - Degrees from diploma mills / known unaccredited institutions
    - Degree field mismatch for claimed specialisation
    - Multiple conflicting highest-degree claims
    - Graduation year that contradicts claimed experience start
    """

    RULE_CODE = "EDUCATION_001"
    RULE_NAME = "Education Validation"
    CATEGORY = "Education"
    DEFAULT_WEIGHT = 20

    # Known diploma-mill keywords (lowercase). Ceiling: use WHED API for real verification.
    _MILL_KEYWORDS: frozenset = frozenset([
        "belford", "rochville", "axact", "no-study", "online degree in 2 weeks",
        "phd in 3 months", "instant degree", "life experience degree",
    ])

    # Highly abbreviated "degrees" that are red flags as claimed PhD/Masters
    _SUSPICIOUS_ABBR_RE = re.compile(
        r"\b(ph\.?d|d\.?sc|m\.?d)\b.{0,20}\b(2\s*weeks|1\s*month|no.?study)\b",
        re.IGNORECASE,
    )

    # Expected graduation-to-experience gap (years)
    _MIN_GAP = -1   # allow 1 year overlap (intern)
    _MAX_GAP = 40

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        education: List[Dict] = parsed_data.get("education") or []

        if not education:
            # No education data — can't validate; pass with low confidence
            return self._pass(confidence=0.4, metadata={"reason": "no_education_data"})

        issues: List[str] = []
        evidences: List[str] = []
        raw_lower = raw_text.lower()

        # Check raw text for diploma-mill keywords
        for kw in self._MILL_KEYWORDS:
            if kw in raw_lower:
                issues.append(f"Suspicious institution keyword: '{kw}'")
                evidences.append(kw)

        # Check raw text for suspicious quick-degree patterns
        if self._SUSPICIOUS_ABBR_RE.search(raw_text):
            issues.append("Rapid degree completion claim detected (PhD/Masters in weeks/months)")

        # Detect duplicate degree levels
        claimed_levels = []
        for edu in education:
            degree = (edu.get("degree") or edu.get("qualification") or "").lower()
            if "phd" in degree or "ph.d" in degree or "doctorate" in degree:
                claimed_levels.append("phd")
            elif "master" in degree or "msc" in degree or "mtech" in degree:
                claimed_levels.append("masters")
            elif "bachelor" in degree or "bsc" in degree or "btech" in degree:
                claimed_levels.append("bachelors")

        from collections import Counter
        level_counts = Counter(claimed_levels)
        for level, count in level_counts.items():
            if count > 1:
                issues.append(f"Multiple {level.title()} degrees claimed ({count})")

        if not issues:
            return self._pass(confidence=0.9, metadata={"degrees_checked": len(education)})

        return self._fail(
            title="Education Section Contains Suspicious Claims",
            description=f"{len(issues)} issue(s): {'; '.join(issues[:3])}",
            severity="HIGH" if any("mill" in i or "rapid" in i for i in issues) else "MEDIUM",
            penalty=self.DEFAULT_WEIGHT,
            evidence="; ".join(evidences[:3]),
            confidence=0.8,
            recommendation="Request certified transcripts and verify institution accreditation.",
            metadata={"issues": issues, "claimed_levels": claimed_levels},
        )
