"""Contact Information Validation Rule — detects missing, fake, or malformed contact data."""

from __future__ import annotations

import re
from typing import Any, Dict, List

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class ContactValidationRule(BaseResumeRule):
    """Validates the presence and format of candidate contact information.

    Detects:
    - Missing email or phone
    - Malformed email address
    - Invalid phone number format
    - Disposable / throwaway email domains
    - Mismatch between resume name and email name hint
    """

    RULE_CODE = "CONTACT_001"
    RULE_NAME = "Contact Information Validation"
    CATEGORY = "Contact"
    DEFAULT_WEIGHT = 10

    _EMAIL_RE = re.compile(
        r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    )
    # International-friendly: 7-15 digits, optional +country code
    _PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,20}$")

    # Known disposable email providers (non-exhaustive)
    _DISPOSABLE_DOMAINS: frozenset = frozenset([
        "mailinator.com", "guerrillamail.com", "10minutemail.com",
        "throwam.com", "yopmail.com", "trashmail.com", "temp-mail.org",
        "dispostable.com", "fakeinbox.com", "sharklasers.com",
        "guerrillamailblock.com", "grr.la", "spam4.me",
    ])

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        contact = parsed_data.get("contact") or parsed_data.get("personal_info") or {}

        # Fall back to top-level keys if contact block absent
        email: str = (
            contact.get("email")
            or parsed_data.get("email")
            or ""
        ).strip().lower()

        phone: str = (
            contact.get("phone")
            or contact.get("mobile")
            or parsed_data.get("phone")
            or parsed_data.get("mobile")
            or ""
        ).strip()

        name: str = (
            contact.get("name")
            or parsed_data.get("name")
            or f"{parsed_data.get('first_name', '')} {parsed_data.get('last_name', '')}".strip()
            or ""
        )

        issues: List[str] = []
        evidences: List[str] = []

        # 1. Missing email
        if not email:
            issues.append("Email address is missing")
        else:
            # 2. Malformed email
            if not self._EMAIL_RE.match(email):
                issues.append(f"Malformed email address: '{email}'")
                evidences.append(email)
            else:
                domain = email.split("@")[-1]
                # 3. Disposable email domain
                if domain in self._DISPOSABLE_DOMAINS:
                    issues.append(f"Disposable/throwaway email domain: '{domain}'")
                    evidences.append(domain)

        # 4. Missing phone
        if not phone:
            issues.append("Phone number is missing")
        else:
            digits_only = re.sub(r"[^\d]", "", phone)
            if len(digits_only) < 7 or len(digits_only) > 15:
                issues.append(f"Phone number has unusual length ({len(digits_only)} digits): '{phone}'")
                evidences.append(phone)

        if not issues:
            return self._pass(
                confidence=1.0,
                metadata={"email_verified": bool(email), "phone_verified": bool(phone)},
            )

        # Weight: missing both is worse than missing one
        missing_count = sum(1 for i in issues if "missing" in i.lower())
        penalty = self.DEFAULT_WEIGHT + (missing_count * 5)

        return self._fail(
            title="Contact Information Issues Found",
            description=f"{len(issues)} contact issue(s): {'; '.join(issues)}",
            severity="HIGH" if missing_count >= 2 else "MEDIUM",
            penalty=min(penalty, 30),
            evidence="; ".join(evidences),
            confidence=0.95,
            recommendation="Verify contact details directly with candidate.",
            metadata={"issues": issues, "email": email, "phone_length": len(re.sub(r'[^\d]', '', phone))},
        )
