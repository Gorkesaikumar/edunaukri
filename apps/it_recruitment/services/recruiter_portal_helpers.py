"""Shared helpers for recruiter portal pages."""

from __future__ import annotations

from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.selectors.company_selector import CompanyMemberSelector


RECRUITER_SIDEBAR_ITEMS = (
    {
        "key": "dashboard",
        "label": "Dashboard",
        "icon": "bi-grid-1x2-fill",
        "url_name": "recruiter_dashboard",
    },
    {
        "key": "post_job",
        "label": "Post New Job",
        "icon": "bi-file-earmark-plus",
        "url_name": "recruiter_job_create",
    },
    {
        "key": "jobs",
        "label": "Manage Jobs",
        "icon": "bi-briefcase",
        "url_name": "recruiter_jobs",
    },
    {
        "key": "candidates",
        "label": "Applications",
        "icon": "bi-person-check",
        "url_name": "recruiter_candidates",
    },
    {
        "key": "shortlisted",
        "label": "Shortlisted",
        "icon": "bi-bookmark-check",
        "url_name": "recruiter_shortlisted_dashboard",
    },
    {
        "key": "interviews",
        "label": "Interviews",
        "icon": "bi-calendar-check",
        "url_name": "recruiter_interviews",
    },
    {
        "key": "selected",
        "label": "Selected",
        "icon": "bi-award",
        "url_name": "recruiter_selected_dashboard",
    },
    {
        "key": "joined",
        "label": "Joined",
        "icon": "bi-person-badge",
        "url_name": "recruiter_joined_dashboard",
    },
    {
        "key": "invoices",
        "label": "Invoices & Billing",
        "icon": "bi-receipt",
        "url_name": "it_recruiter_invoices",
    },
    {
        "key": "analytics",
        "label": "Analytics",
        "icon": "bi-bar-chart",
        "url_name": "recruiter_analytics",
    },
)

RECRUITER_SIDEBAR_SECONDARY = (
    {
        "key": "profile",
        "label": "Company Profile",
        "icon": "bi-building",
        "url_name": "recruiter_profile",
    },
    {
        "key": "saved",
        "label": "Saved Candidates",
        "icon": "bi-bookmark",
        "url_name": "recruiter_saved_candidates",
    },
    {
        "key": "messages",
        "label": "Messages",
        "icon": "bi-chat",
        "url_name": "recruiter_messages",
    },
    {
        "key": "notifications",
        "label": "Notifications",
        "icon": "bi-bell",
        "url_name": "recruiter_notifications",
    },
    {
        "key": "settings",
        "label": "Settings",
        "icon": "bi-gear",
        "url_name": "recruiter_settings",
    },
)


def primary_company_for_recruiter(profile) -> dict | None:
    if not profile:
        return None
    membership = (
        CompanyMemberSelector()
        .for_recruiter(profile)
        .select_related("company")
        .order_by("-is_primary", "-created_at")
        .first()
    )
    if not membership:
        return None
    company = membership.company
    return {
        "id": str(company.pk),
        "name": company.name,
        "verified": company.is_verified,
        "can_publish": company.can_publish_jobs,
    }


def build_recruiter_sidebar_nav(active_key: str, user) -> dict:
    def _item_url(item: dict) -> str:
        url = PortalURLService.recruiter(user, item["url_name"])
        if item.get("url_hash"):
            url = f"{url}{item['url_hash']}"
        return url

    # Dynamic counts
    from apps.applications.models import JobApplication
    from apps.applications.constants.enums import JobApplicationStatus
    from apps.invoices.models import Invoice
    from apps.core.constants.enums import DomainType
    from apps.companies.selectors.company_selector import CompanyMemberSelector

    profile = getattr(user, "recruiter_profile", None)
    company_ids = []
    if profile:
        try:
            company_ids = CompanyMemberSelector().for_recruiter(profile).values_list("company_id", flat=True)
        except Exception:
            pass

    app_count = 0
    shortlisted_count = 0
    interviews_count = 0
    selected_count = 0
    joined_count = 0
    invoices_count = 0

    if company_ids:
        app_count = JobApplication.objects.filter(job_posting__company_id__in=company_ids, is_deleted=False).count()
        shortlisted_count = JobApplication.objects.filter(job_posting__company_id__in=company_ids, status=JobApplicationStatus.SHORTLISTED, is_deleted=False).count()
        interviews_count = JobApplication.objects.filter(job_posting__company_id__in=company_ids, status=JobApplicationStatus.INTERVIEW_SCHEDULED, is_deleted=False).count()
        selected_count = JobApplication.objects.filter(job_posting__company_id__in=company_ids, status=JobApplicationStatus.SELECTED, is_deleted=False).count()
        joined_count = JobApplication.objects.filter(job_posting__company_id__in=company_ids, status=JobApplicationStatus.JOINED, is_deleted=False).count()
        invoices_count = Invoice.objects.filter(bill_to_entity_id__in=company_ids, domain=DomainType.IT, is_deleted=False).count()

    primary = []
    for item in RECRUITER_SIDEBAR_ITEMS:
        d = {**item, "url": _item_url(item), "active": item["key"] == active_key}
        if item["key"] == "candidates":
            d["unread_count"] = app_count
        elif item["key"] == "shortlisted":
            d["unread_count"] = shortlisted_count
        elif item["key"] == "interviews":
            d["unread_count"] = interviews_count
        elif item["key"] == "selected":
            d["unread_count"] = selected_count
        elif item["key"] == "joined":
            d["unread_count"] = joined_count
        elif item["key"] == "invoices":
            d["unread_count"] = invoices_count
        primary.append(d)
        
    secondary = [
        {**item, "url": _item_url(item), "active": item["key"] == active_key}
        for item in RECRUITER_SIDEBAR_SECONDARY
    ]
    return {
        "primary": primary,
        "secondary": secondary,
        "active_key": active_key,
        "user_uuid": str(user.pk),
    }
