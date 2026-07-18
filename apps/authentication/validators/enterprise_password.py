"""Enterprise password policy validation."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError


SPECIAL_CHARS = re.compile(r"[!@#$%^&*(),.?\":{}|<>\[\]\\/_+=\-~`';]")


def validate_enterprise_password(password: str, *, user=None) -> None:
    """Enforce minimum complexity beyond Django defaults."""
    from django.contrib.auth.password_validation import validate_password

    validate_password(password, user=user)
    errors: list[str] = []
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number.")
    if not SPECIAL_CHARS.search(password):
        errors.append("Password must contain at least one special character.")
    if errors:
        raise ValidationError(errors)


def password_strength_score(password: str) -> tuple[int, str]:
    """Return score 0-100 and label for UI meter."""
    if not password:
        return 0, "Enter a password"
    score = 0
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 10
    if re.search(r"[A-Z]", password):
        score += 15
    if re.search(r"[a-z]", password):
        score += 15
    if re.search(r"\d", password):
        score += 20
    if SPECIAL_CHARS.search(password):
        score += 20
    score = min(100, score)
    if score < 40:
        label = "Weak"
    elif score < 70:
        label = "Fair"
    elif score < 90:
        label = "Good"
    else:
        label = "Strong"
    return score, label
