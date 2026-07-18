"""Shared helpers for professor (faculty job seeker) portal pages."""

from __future__ import annotations

from urllib.parse import urlencode

from django.urls import reverse

from apps.applications.constants.faculty_enums import (
    FacultyApplicationStatus,
    FACULTY_TERMINAL_STATUSES,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    format_expected_salary_lpa,
    greeting_for_hour,
    initials_from_name,
    media_url,
)

FACULTY_STATUS_BADGES = {
    FacultyApplicationStatus.APPLIED: ("Applied", "fjd-badge--muted"),
    FacultyApplicationStatus.UNDER_REVIEW: ("Under Review", "fjd-badge--info"),
    FacultyApplicationStatus.SHORTLISTED: ("Shortlisted", "fjd-badge--success"),
    FacultyApplicationStatus.ACADEMIC_VERIFICATION: ("Under Review", "fjd-badge--info"),
    FacultyApplicationStatus.DEPARTMENT_REVIEW: ("Shortlisted", "fjd-badge--success"),
    FacultyApplicationStatus.PRINCIPAL_REVIEW: ("Shortlisted", "fjd-badge--success"),
    FacultyApplicationStatus.MANAGEMENT_APPROVAL: ("Shortlisted", "fjd-badge--success"),
    FacultyApplicationStatus.INTERVIEW_SCHEDULED: (
        "Interview Scheduled",
        "fjd-badge--info",
    ),
    FacultyApplicationStatus.INTERVIEW_COMPLETED: (
        "Interview Completed",
        "fjd-badge--info",
    ),
    FacultyApplicationStatus.OFFER_RELEASED: ("Offer Released", "fjd-badge--success"),
    FacultyApplicationStatus.OFFER_ACCEPTED: ("Offer Accepted", "fjd-badge--success"),
    FacultyApplicationStatus.OFFER_DECLINED: ("Offer Declined", "fjd-badge--muted"),
    FacultyApplicationStatus.SELECTED: ("Selected", "fjd-badge--success"),
    FacultyApplicationStatus.JOINING_IN_PROGRESS: ("Joining in Progress", "fjd-badge--success"),
    FacultyApplicationStatus.JOINED: ("Joined", "fjd-badge--success"),
    FacultyApplicationStatus.REJECTED: ("Rejected", "fjd-badge--danger"),
    FacultyApplicationStatus.WITHDRAWN: ("Withdrawn", "fjd-badge--muted"),
    FacultyApplicationStatus.EXPIRED: ("Expired", "fjd-badge--muted"),
}

WITHDRAW_ALLOWED_STATUSES = frozenset(
    {
        FacultyApplicationStatus.APPLIED,
        FacultyApplicationStatus.UNDER_REVIEW,
        FacultyApplicationStatus.SHORTLISTED,
        FacultyApplicationStatus.ACADEMIC_VERIFICATION,
        FacultyApplicationStatus.DEPARTMENT_REVIEW,
        FacultyApplicationStatus.PRINCIPAL_REVIEW,
        FacultyApplicationStatus.MANAGEMENT_APPROVAL,
    }
)

INTERVIEW_STATUSES = frozenset(
    {
        FacultyApplicationStatus.INTERVIEW_SCHEDULED,
        FacultyApplicationStatus.INTERVIEW_COMPLETED,
    }
)

OFFER_STATUSES = frozenset(
    {
        FacultyApplicationStatus.OFFER_RELEASED,
        FacultyApplicationStatus.OFFER_ACCEPTED,
        FacultyApplicationStatus.OFFER_DECLINED,
    }
)


def faculty_status_ui(status: str) -> tuple[str, str]:
    return FACULTY_STATUS_BADGES.get(
        status, (status.replace("_", " ").title(), "fjd-badge--muted")
    )


PROFESSOR_SIDEBAR_ITEMS = (
    {
        "key": "dashboard",
        "label": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "url_name": "professor_dashboard",
    },
    {
        "key": "browse_jobs",
        "label": "Job Search",
        "icon": "bi-search",
        "url_name": "professor_browse_jobs",
    },
    {
        "key": "applications",
        "label": "Applications",
        "icon": "bi-file-earmark-text",
        "url_name": "professor_applications",
    },
    {
        "key": "saved_jobs",
        "label": "Saved Jobs",
        "icon": "bi-bookmark",
        "url_name": "professor_saved_jobs",
    },
    {
        "key": "tracker",
        "label": "Tracker",
        "icon": "bi-bullseye",
        "url_name": "professor_tracker",
    },
    {
        "key": "interviews",
        "label": "Interviews",
        "icon": "bi-calendar-event",
        "url_name": "professor_interviews",
    },
    {
        "key": "resume",
        "label": "Resume / CV",
        "icon": "bi-file-earmark-text",
        "url_name": "professor_resume",
    },
    {
        "key": "certificates",
        "label": "Certificates",
        "icon": "bi-award",
        "url_name": "professor_certificates",
    },
    {
        "key": "profile",
        "label": "Profile",
        "icon": "bi-person",
        "url_name": "professor_profile",
    },
)
PROFESSOR_SIDEBAR_SECONDARY = (
    {
        "key": "research",
        "label": "Research & Publications",
        "icon": "bi-journal-text",
        "url_name": "professor_research",
    },
    {
        "key": "settings",
        "label": "Settings",
        "icon": "bi-gear",
        "url_name": "professor_settings",
    },
)


def build_professor_sidebar(active_key: str, user) -> dict:
    primary = []
    for item in PROFESSOR_SIDEBAR_ITEMS:
        url = _sidebar_url(item["url_name"], user)
        primary.append({**item, "url": url, "active": item["key"] == active_key})
    secondary = []
    for item in PROFESSOR_SIDEBAR_SECONDARY:
        url = _sidebar_url(item["url_name"], user)
        secondary.append({**item, "url": url, "active": item["key"] == active_key})
    return {
        "primary": primary,
        "secondary": secondary,
        "active_key": active_key,
        "user_uuid": str(user.pk),
    }


def _sidebar_url(url_name: str, user) -> str:
    if url_name.startswith("professor_"):
        return PortalURLService.professor(user, url_name)
    return reverse(url_name)


def build_pagination_query(page: int, **params) -> str:
    """Build relative query string preserving list filters."""
    query = {k: v for k, v in params.items() if v not in (None, "", False)}
    if page > 1:
        query["page"] = page
    encoded = urlencode(query)
    return f"?{encoded}" if encoded else ""


def application_filters_query(page: int, filters: dict) -> str:
    return build_pagination_query(
        page,
        q=filters.get("q") or "",
        status=filters.get("status") or "",
        active="1" if filters.get("active_only") else "",
        interview="1" if filters.get("interview_only") else "",
        offer="1" if filters.get("offer_only") else "",
        rejected="1" if filters.get("rejected_only") else "",
    )


def interview_filters_query(page: int, filters: dict) -> str:
    return build_pagination_query(
        page,
        q=filters.get("q") or "",
        status=filters.get("status") or "",
    )


def institution_profile_url(college) -> str | None:
    slug = getattr(college, "slug", None)
    if slug:
        return reverse("institution_detail", kwargs={"slug": slug})
    return None


__all__ = [
    "application_filters_query",
    "build_professor_sidebar",
    "build_pagination_query",
    "faculty_status_ui",
    "format_expected_salary_lpa",
    "greeting_for_hour",
    "initials_from_name",
    "institution_profile_url",
    "interview_filters_query",
    "media_url",
    "FACULTY_STATUS_BADGES",
    "PROFESSOR_SIDEBAR_ITEMS",
]
