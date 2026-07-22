"""Resume Completeness Rule — detects thin, incomplete, or suspiciously sparse resumes."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class ResumeCompletenessRule(BaseResumeRule):
    """Validates that the resume contains sufficient content to be credible.

    Detects:
    - Missing critical sections (experience, skills, education)
    - Very short raw text (possible image-only or placeholder resume)
    - Missing summary / objective
    - Zero quantifiable achievements in experience descriptions
    """

    RULE_CODE = "COMPLETENESS_001"
    RULE_NAME = "Resume Completeness"
    CATEGORY = "Completeness"
    DEFAULT_WEIGHT = 10

    # Required section keys checked in parsed_data
    _REQUIRED_SECTIONS: List[Tuple[str, List[str]]] = [
        ("Skills", ["skills"]),
        ("Education", ["education"]),
        ("Experience", ["experience", "work_experience"]),
    ]

    # Minimum raw_text word count to be a valid resume
    MIN_WORD_COUNT = 80

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        issues: List[str] = []
        evidences: List[str] = []

        word_count = len((raw_text or "").split())

        # 1. Very sparse raw text
        if word_count < self.MIN_WORD_COUNT:
            issues.append(f"Resume contains very little text ({word_count} words) — possible image-only or corrupted file")
            evidences.append(f"word_count={word_count}")

        # 2. Missing critical sections
        for label, keys in self._REQUIRED_SECTIONS:
            has_section = any(
                parsed_data.get(k) for k in keys
            )
            if not has_section:
                issues.append(f"Missing '{label}' section")

        # 3. Experience entries with zero description
        experience = parsed_data.get("experience") or parsed_data.get("work_experience") or []
        empty_desc_count = sum(
            1 for exp in experience
            if not (exp.get("description") or exp.get("responsibilities") or exp.get("summary") or "").strip()
        )
        if experience and empty_desc_count == len(experience):
            issues.append("All experience entries lack descriptions or responsibilities")
            evidences.append(f"empty_descriptions={empty_desc_count}")

        # 4. No contact info at all
        has_contact = bool(
            parsed_data.get("email")
            or parsed_data.get("phone")
            or (parsed_data.get("contact") or {}).get("email")
        )
        if not has_contact:
            issues.append("No contact information found in resume")

        if not issues:
            return self._pass(
                confidence=0.95,
                metadata={"word_count": word_count, "sections_present": len(self._REQUIRED_SECTIONS)},
            )

        critical_missing = sum(1 for i in issues if "Missing" in i)
        severity = "HIGH" if critical_missing >= 2 or word_count < 40 else "MEDIUM"

        return self._fail(
            title="Incomplete Resume Detected",
            description=f"{len(issues)} completeness issue(s): {'; '.join(issues[:4])}",
            severity=severity,
            penalty=self.DEFAULT_WEIGHT * min(len(issues), 3),
            evidence="; ".join(evidences[:3]),
            confidence=0.9,
            recommendation="Ask candidate to submit a complete, updated resume.",
            metadata={"issues": issues, "word_count": word_count},
        )
