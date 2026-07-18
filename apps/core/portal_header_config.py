"""Shared portal dashboard header configuration (IT Job Seeker reference)."""

from __future__ import annotations

from typing import Any

IT_JOB_SEEKER_HEADER: dict[str, Any] = {
    "mobile_sidebar_id": "jsdMobileSidebar",
    "dashboard_route": "jobseeker_dashboard",
    "search_placeholder": "Search for careers, institutions, or courses...",
    "search_placeholder_mobile": "Search careers, institutions...",
    "search_aria_label": "Search careers and institutions",
    "profile_menu": (
        {
            "label": "My Dashboard",
            "icon": "bi-grid-1x2",
            "route": "jobseeker_dashboard",
        },
        {"label": "My Profile", "icon": "bi-person", "route": "jobseeker_profile"},
        {
            "label": "Resume",
            "icon": "bi-file-earmark-text",
            "route": "jobseeker_resume",
        },
        {
            "label": "Applications",
            "icon": "bi-briefcase",
            "route": "jobseeker_applications",
        },
        {"label": "Settings", "icon": "bi-gear", "route": "jobseeker_settings"},
    ),
}

FACULTY_JOB_SEEKER_HEADER: dict[str, Any] = {
    "mobile_sidebar_id": "fjdMobileSidebar",
    "dashboard_route": "professor_dashboard",
    "search_placeholder": "Search for faculty roles, institutions, or courses...",
    "search_placeholder_mobile": "Search faculty roles, institutions...",
    "search_aria_label": "Search faculty roles and institutions",
    "profile_menu": (
        {
            "label": "My Dashboard",
            "icon": "bi-grid-1x2",
            "route": "professor_dashboard",
        },
        {"label": "My Profile", "icon": "bi-person", "route": "professor_profile"},
        {
            "label": "Resume",
            "icon": "bi-file-earmark-text",
            "route": "professor_resume",
        },
        {
            "label": "Applications",
            "icon": "bi-briefcase",
            "route": "professor_applications",
        },
        {"label": "Settings", "icon": "bi-gear", "route": "professor_settings"},
    ),
}

INSTITUTION_RECRUITER_HEADER: dict[str, Any] = {
    "mobile_sidebar_id": "icdMobileSidebar",
    "dashboard_route": "college_dashboard",
    "search_placeholder": "Search vacancies, departments, or applicants...",
    "search_placeholder_mobile": "Search vacancies, applicants...",
    "search_aria_label": "Search institution vacancies and applicants",
    "profile_menu": (
        {"label": "Dashboard", "icon": "bi-grid-1x2", "route": "college_dashboard"},
        {
            "label": "Institution Profile",
            "icon": "bi-building",
            "route": "college_profile",
        },
        {"label": "Vacancies", "icon": "bi-mortarboard", "route": "college_vacancies"},
        {
            "label": "Applications",
            "icon": "bi-person-check",
            "route": "college_applications",
        },
        {"label": "Settings", "icon": "bi-gear", "route": "college_settings"},
    ),
}
