"""Company Validation Rule — detects suspicious or unverifiable employer claims."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class CompanyValidationRule(BaseResumeRule):
    """Validates that claimed employers are real, verifiable, and consistently described.

    Detects:
    - Generic/placeholder company names (e.g. 'Company XYZ', 'ABC Corp')
    - Very short tenures at prestigious firms (possible name-dropping)
    - Same company listed multiple times with different roles but identical dates
    - No company names at all despite claimed experience
    """

    RULE_CODE = "COMPANY_001"
    RULE_NAME = "Company Validation"
    CATEGORY = "Employment"
    DEFAULT_WEIGHT = 20

    # Regex patterns for obviously placeholder company names
    _PLACEHOLDER_RE = re.compile(
        r"^(company\s*(xyz|abc|name|pvt|ltd|llc|inc)?|abc\s*(corp|company|pvt|ltd)?|"
        r"xyz\s*(corp|company|pvt|ltd)?|some\s*company|your\s*company|employer\s*name|"
        r"organisation\s*name|organization\s*name|n/?a|na|tbd|tba|confidential)$",
        re.IGNORECASE,
    )

    # Extremely short tenure at a firm is a flag (< 1 month in same year = suspicious)
    _YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

    # Known prestigious firm name-drops worth flagging if tenure < 3 months
    _PRESTIGIOUS: frozenset = frozenset([
        "google", "amazon", "meta", "microsoft", "apple", "netflix",
        "openai", "deepmind", "spacex", "mckinsey", "goldman sachs",
        "morgan stanley", "jpmorgan", "nasa", "isro",
    ])

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        experience: List[Dict] = parsed_data.get("experience") or parsed_data.get("work_experience") or []

        if not experience:
            return self._pass(confidence=0.5, metadata={"reason": "no_experience_data"})

        issues: List[str] = []
        evidences: List[str] = []
        seen_companies: Dict[str, List] = {}

        for exp in experience:
            company = (exp.get("company") or exp.get("organization") or "").strip()
            if not company:
                issues.append("Experience entry with no company name")
                continue

            company_lower = company.lower()

            # 1. Placeholder name
            if self._PLACEHOLDER_RE.match(company_lower):
                issues.append(f"Placeholder company name: '{company}'")
                evidences.append(company)
                continue

            # 2. Duplicate company with same date range
            start = str(exp.get("start_date") or exp.get("from") or "")
            end = str(exp.get("end_date") or exp.get("to") or "")
            key = f"{company_lower}|{start}|{end}"
            if key in seen_companies:
                issues.append(f"Duplicate company entry with same dates: '{company}'")
                evidences.append(company)
            else:
                seen_companies[key] = exp

            # 3. Prestigious firm with suspicious very short tenure
            if any(pf in company_lower for pf in self._PRESTIGIOUS):
                start_yr = self._extract_year(start)
                end_yr = self._extract_year(end)
                if start_yr and end_yr and start_yr == end_yr:
                    # Same year — potentially < 1 year at a prestigious firm — flag for review
                    issues.append(
                        f"Very short tenure (<1 year) at prestigious firm: '{company}' ({start_yr})"
                    )
                    evidences.append(f"{company} {start_yr}")

        if not issues:
            return self._pass(
                confidence=0.85,
                metadata={"companies_validated": len(experience)},
            )

        severity = "HIGH" if any("Placeholder" in i or "Duplicate" in i for i in issues) else "MEDIUM"
        return self._fail(
            title="Company Information Suspicious",
            description=f"{len(issues)} employer issue(s): {'; '.join(issues[:3])}",
            severity=severity,
            penalty=self.DEFAULT_WEIGHT,
            evidence="; ".join(evidences[:3]),
            confidence=0.8,
            recommendation="Verify employment via references or offer letter.",
            metadata={"issues": issues, "companies_checked": len(experience)},
        )

    @staticmethod
    def _extract_year(text: str):
        m = re.search(r"\b(19|20)\d{2}\b", text)
        return int(m.group()) if m else None
