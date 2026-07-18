"""Shared helpers for institution (college recruiter) portal pages."""

from __future__ import annotations

from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.authentication.services.portal_url_service import PortalURLService
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    greeting_for_hour,
    initials_from_name,
    media_url,
)

INSTITUTION_STATUS_BADGES = {
    FacultyApplicationStatus.APPLIED: ("Applied", "icd-badge--muted"),
    FacultyApplicationStatus.UNDER_REVIEW: ("Under Review", "icd-badge--info"),
    FacultyApplicationStatus.SHORTLISTED: ("Shortlisted", "icd-badge--success"),
    FacultyApplicationStatus.ACADEMIC_VERIFICATION: ("Shortlisted", "icd-badge--success"),
    FacultyApplicationStatus.DEPARTMENT_REVIEW: ("Shortlisted", "icd-badge--success"),
    FacultyApplicationStatus.PRINCIPAL_REVIEW: ("Shortlisted", "icd-badge--success"),
    FacultyApplicationStatus.MANAGEMENT_APPROVAL: ("Shortlisted", "icd-badge--success"),
    FacultyApplicationStatus.INTERVIEW_SCHEDULED: ("Interview Scheduled", "icd-badge--secondary"),
    FacultyApplicationStatus.INTERVIEW_COMPLETED: ("Interview Completed", "icd-badge--secondary"),
    FacultyApplicationStatus.OFFER_RELEASED: ("Offer Released", "icd-badge--success"),
    FacultyApplicationStatus.OFFER_ACCEPTED: ("Offer Accepted", "icd-badge--success"),
    FacultyApplicationStatus.OFFER_DECLINED: ("Offer Declined", "icd-badge--muted"),
    FacultyApplicationStatus.SELECTED: ("Selected", "icd-badge--emerald"),
    FacultyApplicationStatus.JOINING_IN_PROGRESS: ("Joining In Progress", "icd-badge--warning"),
    FacultyApplicationStatus.JOINED: ("Joined", "icd-badge--darkgreen"),
    FacultyApplicationStatus.REJECTED: ("Rejected", "icd-badge--danger"),
    FacultyApplicationStatus.WITHDRAWN: ("Withdrawn", "icd-badge--muted"),
    FacultyApplicationStatus.EXPIRED: ("Expired", "icd-badge--muted"),
}

COLLEGE_SIDEBAR_ITEMS = (
    {
        "key": "dashboard",
        "label": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "url_name": "college_dashboard",
    },
    {
        "key": "post_vacancy",
        "label": "Post Vacancy",
        "icon": "bi-file-earmark-plus",
        "url_name": "college_vacancy_create",
    },
    {
        "key": "vacancies",
        "label": "Manage Vacancies",
        "icon": "bi-mortarboard",
        "url_name": "college_vacancies",
    },
    {
        "key": "applications",
        "label": "Applications",
        "icon": "bi-person-check",
        "url_name": "college_applications",
    },
    {
        "key": "shortlisted",
        "label": "Shortlisted",
        "icon": "bi-bookmark-check",
        "url_name": "college_shortlisted_dashboard",
    },
    {
        "key": "interviews",
        "label": "Interviews",
        "icon": "bi-calendar-event",
        "url_name": "college_interviews",
    },
    {
        "key": "selected",
        "label": "Selected",
        "icon": "bi-award",
        "url_name": "college_selected_dashboard",
    },
    {
        "key": "joined",
        "label": "Joined",
        "icon": "bi-person-badge",
        "url_name": "college_joined_dashboard",
    },
    {
        "key": "invoices",
        "label": "Invoices & Billing",
        "icon": "bi-receipt",
        "url_name": "college_invoices",
    },
    {
        "key": "analytics",
        "label": "Analytics",
        "icon": "bi-bar-chart",
        "url_name": "college_analytics",
    },
)

COLLEGE_SIDEBAR_SECONDARY = (
    {
        "key": "profile",
        "label": "Institution Profile",
        "icon": "bi-building",
        "url_name": "college_profile",
    },
    {
        "key": "messages",
        "label": "Messages",
        "icon": "bi-chat",
        "url_name": "college_messages",
    },
    {
        "key": "notifications",
        "label": "Notifications",
        "icon": "bi-bell",
        "url_name": "college_notifications",
    },
    {
        "key": "settings",
        "label": "Settings",
        "icon": "bi-gear",
        "url_name": "college_settings",
    },
)


def institution_status_ui(status: str) -> tuple[str, str]:
    return INSTITUTION_STATUS_BADGES.get(
        status, (status.replace("_", " ").title(), "icd-badge--muted")
    )


def primary_institution_for_user(college_user) -> dict | None:
    membership = (
        CollegeMemberSelector()
        .for_user(college_user)
        .select_related("college", "college__logo_file")
        .order_by("-is_primary", "-created_at")
        .first()
    )
    if not membership:
        return None
    college = membership.college
    return {
        "id": str(college.pk),
        "name": college.name,
        "city": college.city or "",
        "verified": college.is_verified,
        "verification_status": "verified",
        "verification_label": "Verified",
        "can_publish": college.can_publish_vacancies,
        "logo_url": media_url(college.logo_file),
    }


def build_college_sidebar(active_key: str, user) -> dict:
    def _item_url(item: dict) -> str:
        return PortalURLService.college(user, item["url_name"])

    from apps.notifications.models import Notification

    unread_applications_count = Notification.objects.filter(
        recipient_domain="college",
        recipient_id=user.pk,
        event_type="NEW_FACULTY_APPLICATION",
        is_read=False,
    ).count()

    primary = []
    for item in COLLEGE_SIDEBAR_ITEMS:
        d = {**item, "url": _item_url(item), "active": item["key"] == active_key}
        if item["key"] == "applications":
            d["unread_count"] = unread_applications_count
        primary.append(d)
    secondary = [
        {**item, "url": _item_url(item), "active": item["key"] == active_key}
        for item in COLLEGE_SIDEBAR_SECONDARY
    ]
    return {
        "primary": primary,
        "secondary": secondary,
        "active_key": active_key,
        "user_uuid": str(user.pk),
    }


__all__ = [
    "COLLEGE_SIDEBAR_ITEMS",
    "COLLEGE_SIDEBAR_SECONDARY",
    "INSTITUTION_STATUS_BADGES",
    "build_college_sidebar",
    "greeting_for_hour",
    "initials_from_name",
    "institution_status_ui",
    "media_url",
    "primary_institution_for_user",
]
