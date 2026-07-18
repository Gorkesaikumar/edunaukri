"""Shared helpers for job seeker portal pages."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse


def media_url(stored_file) -> str | None:
    if not stored_file or not getattr(stored_file, "storage_path", None):
        return None
    path = stored_file.storage_path.lstrip("/")
    return f"{settings.MEDIA_URL}{path}"


def initials_from_name(name: str, fallback: str = "U") -> str:
    parts = (name or "").strip().split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    if parts and parts[0]:
        token = parts[0]
        return token[:2].upper() if len(token) >= 2 else token[0].upper()
    return fallback[:2].upper() if fallback else "U"


def format_salary_lpa(min_salary, max_salary, currency: str = "INR") -> str:
    """Format salary range in Indian Lakhs notation."""

    def _to_lpa(value):
        if value is None:
            return None
        return salary_inr_to_lpa_amount(value)

    lo = _to_lpa(min_salary)
    hi = _to_lpa(max_salary)
    symbol = "₹" if currency == "INR" else f"{currency} "
    if lo is not None and hi is not None:
        lo_s = f"{lo:.0f}L" if lo >= 1 else f"{lo:.1f}L"
        hi_s = f"{hi:.0f}L" if hi >= 1 else f"{hi:.1f}L"
        if lo == hi:
            return f"{symbol}{lo_s} PA"
        return f"{symbol}{lo_s} - {symbol}{hi_s} PA"
    if lo is not None:
        return f"{symbol}{lo:.0f}L+ PA"
    if hi is not None:
        return f"Up to {symbol}{hi:.0f}L PA"
    return "Not disclosed"


def salary_inr_to_lpa_amount(value) -> float | None:
    """Convert stored INR salary to LPA; tolerate legacy values entered as LPA."""
    if value is None:
        return None
    inr = float(value)
    # Before LPA UX, small numbers (e.g. 12) were saved as LPA directly.
    if inr < 10_000:
        return inr
    return inr / 100_000


def salary_lpa_to_inr(lpa) -> "Decimal":
    """Convert LPA input to INR for database storage."""
    from decimal import Decimal, InvalidOperation

    if lpa in (None, ""):
        return None
    try:
        amount = Decimal(str(lpa))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid salary value.") from exc
    if amount <= 0:
        raise ValueError("Salary must be greater than zero.")
    if amount > 500:
        raise ValueError("Salary cannot exceed 500 LPA.")
    return (amount * Decimal("100000")).quantize(Decimal("0.01"))


def salary_inr_to_lpa_form_value(value) -> str | None:
    """Format stored salary as LPA for form inputs."""
    lpa = salary_inr_to_lpa_amount(value)
    if lpa is None:
        return None
    if lpa == int(lpa):
        return str(int(lpa))
    return f"{lpa:g}"


def format_expected_salary_lpa(salary, currency: str = "INR") -> str:
    """Format a single expected annual salary value."""
    if salary is None:
        return "—"
    lpa = salary_inr_to_lpa_amount(salary)
    if lpa is None:
        return "—"
    symbol = "₹" if currency == "INR" else f"{currency} "
    lpa_s = f"{lpa:.0f}L" if lpa >= 1 else f"{lpa:.1f}L"
    return f"{symbol}{lpa_s} PA"


def greeting_for_hour(hour: int) -> str:
    if hour < 12:
        return "Good Morning"
    if hour < 17:
        return "Good Afternoon"
    return "Good Evening"


JOBSEEKER_SIDEBAR_ITEMS = (
    {
        "key": "dashboard",
        "label": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "url_name": "jobseeker_dashboard",
    },
    {
        "key": "profile",
        "label": "My Profile",
        "icon": "bi-person",
        "url_name": "jobseeker_profile",
    },
    {
        "key": "browse_jobs",
        "label": "Browse Jobs",
        "icon": "bi-search",
        "url_name": "marketplace_browse_jobs",
    },
    {
        "key": "saved_jobs",
        "label": "Saved Jobs",
        "icon": "bi-bookmark",
        "url_name": "jobseeker_saved_jobs",
    },
    {
        "key": "applications",
        "label": "Applied Jobs",
        "icon": "bi-check2-square",
        "url_name": "jobseeker_applications",
    },
    {
        "key": "tracker",
        "label": "Tracker",
        "icon": "bi-bullseye",
        "url_name": "jobseeker_tracker",
    },
    {
        "key": "interviews",
        "label": "Interviews",
        "icon": "bi-calendar-event",
        "url_name": "jobseeker_interviews",
    },
)
JOBSEEKER_SIDEBAR_SECONDARY = (
    {
        "key": "resume",
        "label": "Resume",
        "icon": "bi-file-earmark-text",
        "url_name": "jobseeker_resume",
    },
    {
        "key": "certificates",
        "label": "Certificates",
        "icon": "bi-award",
        "url_name": "jobseeker_certificates",
    },
    {
        "key": "settings",
        "label": "Settings",
        "icon": "bi-gear",
        "url_name": "jobseeker_settings",
    },
)


def build_sidebar_nav(active_key: str, user) -> dict:
    from apps.authentication.services.portal_url_service import PortalURLService

    def _item_url(url_name: str) -> str:
        if url_name.startswith("jobseeker_"):
            return PortalURLService.jobseeker(user, url_name)
        return reverse(url_name)

    primary = []
    for item in JOBSEEKER_SIDEBAR_ITEMS:
        primary.append(
            {
                **item,
                "url": _item_url(item["url_name"]),
                "active": item["key"] == active_key,
            }
        )
    secondary = []
    for item in JOBSEEKER_SIDEBAR_SECONDARY:
        secondary.append(
            {
                **item,
                "url": _item_url(item["url_name"]),
                "active": item["key"] == active_key,
            }
        )
    return {
        "primary": primary,
        "secondary": secondary,
        "active_key": active_key,
        "user_uuid": str(user.pk),
    }
