"""Shared auth page context for IT and Faculty web flows."""

from __future__ import annotations

from django.urls import reverse

DOMAIN_META = {
    "it": {
        "portal_label": "IT Recruitment",
        "roles": {
            "seeker": {
                "label": "Job Seeker",
                "login_url_name": "it_login_job_seeker",
                "signup_url_name": "it_signup_job_seeker",
            },
            "recruiter": {
                "label": "Recruiter",
                "login_url_name": "it_login_recruiter",
                "signup_url_name": "it_signup_recruiter",
            },
        },
        "default_role": "seeker",
        "domain_selection_url_name": "domain_selection",
    },
    "professor": {
        "portal_label": "Faculty Portal",
        "roles": {
            "seeker": {
                "label": "Faculty Job Seeker",
                "login_url_name": "faculty_login_professor",
                "signup_url_name": "faculty_signup_professor",
            },
        },
        "default_role": "seeker",
        "domain_selection_url_name": "domain_selection",
    },
    "college": {
        "portal_label": "Faculty Portal",
        "roles": {
            "institution": {
                "label": "Institution",
                "login_url_name": "faculty_login_institution",
                "signup_url_name": "faculty_signup_institution",
            },
        },
        "default_role": "institution",
        "domain_selection_url_name": "domain_selection",
    },
}


def resolve_auth_portal_context(
    request, *, page: str, domain: str | None = None
) -> dict:
    domain = (
        domain or request.GET.get("domain") or request.POST.get("domain") or "it"
    ).strip()
    role = (request.GET.get("role") or request.POST.get("role") or "").strip()

    meta = DOMAIN_META.get(domain, DOMAIN_META["it"])
    if not role:
        role = meta["default_role"]
    role_meta = meta["roles"].get(role) or next(iter(meta["roles"].values()))

    login_url = reverse(role_meta["login_url_name"])
    signup_url = reverse(role_meta["signup_url_name"])
    forgot_url = reverse("web_forgot_password")

    return {
        "page": page,
        "domain": domain,
        "role": role,
        "role_label": role_meta["label"],
        "portal_label": meta["portal_label"],
        "login_url": login_url,
        "signup_url": signup_url,
        "forgot_password_url": f"{forgot_url}?domain={domain}&role={role}",
        "domain_selection_url": reverse(meta["domain_selection_url_name"]),
    }
