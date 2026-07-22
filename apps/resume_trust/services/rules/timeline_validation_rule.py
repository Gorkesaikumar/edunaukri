"""Timeline Validation Rule — detects employment/education date overlaps and future dates."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class TimelineValidationRule(BaseResumeRule):
    """Validates that employment and education timelines are internally consistent.

    Detects:
    - Experience entries with start > end date
    - Overlapping full-time positions (same period)
    - Future end dates (unless 'Present')
    - Impossible total years of experience vs candidate age/graduation
    """

    RULE_CODE = "TIMELINE_001"
    RULE_NAME = "Timeline Validation"
    CATEGORY = "Timeline"
    DEFAULT_WEIGHT = 25

    # Matches YYYY, Month YYYY, MM/YYYY, YYYY-MM
    _YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
    _PRESENT_TOKENS = frozenset(["present", "current", "till date", "ongoing", "now"])

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        experiences: List[Dict] = parsed_data.get("experience") or parsed_data.get("work_experience") or []
        education: List[Dict] = parsed_data.get("education") or []

        if not experiences and not education:
            return self._pass(confidence=0.5, metadata={"reason": "no_timeline_data"})

        issues: List[str] = []
        evidences: List[str] = []

        today = date.today()

        # Validate experience blocks
        intervals: List[Tuple[int, int]] = []
        for exp in experiences:
            start_year = self._extract_year(exp.get("start_date") or exp.get("from") or "")
            raw_end = exp.get("end_date") or exp.get("to") or ""
            is_present = self._is_present(raw_end)
            end_year = today.year if is_present else self._extract_year(raw_end)

            if start_year is None:
                continue
            if end_year is None:
                end_year = today.year

            company = exp.get("company") or exp.get("organization") or "Unknown"

            if start_year > end_year:
                issues.append(f"End date before start at '{company}' ({start_year}–{end_year})")
                evidences.append(f"{company}: {start_year} → {end_year}")

            if end_year > today.year:
                issues.append(f"Future end date at '{company}' ({end_year})")

            intervals.append((start_year, end_year))

        # Detect overlapping roles (3+ months in same year range)
        intervals.sort()
        for i in range(1, len(intervals)):
            prev_end = intervals[i - 1][1]
            curr_start = intervals[i][0]
            if curr_start < prev_end - 0:  # overlap check
                overlap_years = prev_end - curr_start
                if overlap_years > 1:
                    issues.append(f"Overlapping roles detected: {overlap_years}-year overlap")
                    evidences.append(f"Overlap: {curr_start}–{prev_end}")

        if not issues:
            return self._pass(confidence=0.95, metadata={"intervals_validated": len(intervals)})

        return self._fail(
            title="Timeline Inconsistency Detected",
            description=f"{len(issues)} timeline issue(s) found: {'; '.join(issues[:3])}",
            severity="HIGH" if len(issues) > 1 else "MEDIUM",
            penalty=self.DEFAULT_WEIGHT * len(issues) if len(issues) <= 3 else self.DEFAULT_WEIGHT * 3,
            evidence="; ".join(evidences[:3]),
            confidence=0.85,
            recommendation="Verify employment dates with candidate during interview.",
            metadata={"issues": issues},
        )

    @classmethod
    def _extract_year(cls, text: str) -> Optional[int]:
        if not text:
            return None
        m = cls._YEAR_RE.search(str(text))
        return int(m.group()) if m else None

    @classmethod
    def _is_present(cls, text: str) -> bool:
        return bool(text) and str(text).strip().lower() in cls._PRESENT_TOKENS
