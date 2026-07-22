"""Certification Validation Rule — detects fake, expired, or unverifiable certifications."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class CertificationValidationRule(BaseResumeRule):
    """Validates certifications listed on the resume.

    Detects:
    - Certifications with past expiry dates (and not listed as perpetual)
    - Certifications without an issuing body
    - Known-fake or unaccredited credential patterns
    - Unrealistic certification count (quantity stuffing)
    - Missing credential ID for verifiable certs
    """

    RULE_CODE = "CERT_001"
    RULE_NAME = "Certification Validation"
    CATEGORY = "Certifications"
    DEFAULT_WEIGHT = 15

    # Certifications that are time-limited and require renewal
    _EXPIRABLE_CERTS: frozenset = frozenset([
        "aws", "azure", "gcp", "google cloud", "cisco", "ccna", "ccnp", "ccie",
        "comptia", "pmp", "scrum", "prince2", "ceh", "cissp", "cisa",
        "salesforce", "red hat", "rhce", "rhcsa",
    ])

    # Certifications that issue verifiable IDs
    _VERIFIABLE_CERTS: frozenset = frozenset([
        "aws", "azure", "google cloud", "cisco", "pmp", "ceh", "cissp",
        "salesforce", "oracle", "comptia",
    ])

    # Suspicious patterns in cert names
    _SUSPICIOUS_RE = re.compile(
        r"(lifetime\s+expert|world\s+record|instant\s+cert|no\s+exam|"
        r"auto[\-\s]?cert|free\s+certification\s+guarantee)",
        re.IGNORECASE,
    )

    _YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

    # Flag if more than this many certs listed
    CERT_COUNT_WARNING = 15

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        certs: List[Dict] = (
            parsed_data.get("certifications")
            or parsed_data.get("certificates")
            or []
        )

        if not certs:
            return self._pass(confidence=0.6, metadata={"reason": "no_certifications"})

        issues: List[str] = []
        evidences: List[str] = []
        today = date.today()

        # 1. Quantity stuffing
        if len(certs) > self.CERT_COUNT_WARNING:
            issues.append(f"Unusually high certification count: {len(certs)}")
            evidences.append(f"{len(certs)} certs")

        for cert in certs:
            name: str = (cert.get("name") or cert.get("title") or cert.get("certification") or "").strip()
            issuer: str = (cert.get("issuer") or cert.get("organization") or cert.get("issued_by") or "").strip()
            expiry_raw: str = str(cert.get("expiry_date") or cert.get("valid_until") or cert.get("expiry") or "").strip()
            credential_id: str = (cert.get("credential_id") or cert.get("id") or "").strip()
            name_lower = name.lower()

            if not name:
                continue

            # 2. No issuing body
            if not issuer:
                issues.append(f"Certification '{name}' has no issuing body listed")

            # 3. Suspicious cert patterns
            if self._SUSPICIOUS_RE.search(name):
                issues.append(f"Suspicious certification name: '{name}'")
                evidences.append(name)

            # 4. Expired certifications
            expiry_year = self._extract_year(expiry_raw)
            if expiry_year and expiry_year < today.year:
                is_expirable = any(kw in name_lower for kw in self._EXPIRABLE_CERTS)
                if is_expirable:
                    issues.append(f"Expired certification: '{name}' (expired {expiry_year})")
                    evidences.append(f"{name} expired {expiry_year}")

            # 5. Verifiable cert missing credential ID
            is_verifiable = any(kw in name_lower for kw in self._VERIFIABLE_CERTS)
            if is_verifiable and not credential_id:
                issues.append(f"'{name}' should have a verifiable credential ID")

        if not issues:
            return self._pass(
                confidence=0.85,
                metadata={"certs_validated": len(certs)},
            )

        has_suspicious = any("Suspicious" in i or "fake" in i.lower() for i in issues)
        has_expired = any("Expired" in i for i in issues)
        severity = "HIGH" if has_suspicious else "MEDIUM" if has_expired else "LOW"

        return self._fail(
            title="Certification Issues Detected",
            description=f"{len(issues)} certification issue(s): {'; '.join(issues[:4])}",
            severity=severity,
            penalty=self.DEFAULT_WEIGHT,
            evidence="; ".join(evidences[:3]),
            confidence=0.8,
            recommendation="Request original certificates and verify credential IDs on issuer portals.",
            metadata={"issues": issues, "certs_checked": len(certs)},
        )

    @staticmethod
    def _extract_year(text: str) -> Optional[int]:
        m = re.search(r"\b(19|20)\d{2}\b", text)
        return int(m.group()) if m else None
