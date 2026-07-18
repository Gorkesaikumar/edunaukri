"""Allowed search fields, filters, and sort options per resource."""

from apps.search.constants.enums import SearchResource

MAX_QUERY_LENGTH = 200
MIN_QUERY_LENGTH = 1

RESOURCE_CONFIG = {
    SearchResource.JOBS: {
        "query_param": "q",
        "search_fields": ("title", "description", "job_code", "company_name_snapshot"),
        "filter_fields": {
            "location": "str",
            "employment_type": "str",
            "work_mode": "str",
            "is_remote": "bool",
            "skills": "list",
            "experience": "int",
            "salary_min": "decimal",
            "salary_max": "decimal",
            "exclude_employment_type": "str",
        },
        "sort_fields": ("recent", "oldest", "salary_high", "salary_low", "title"),
        "default_sort": "recent",
    },
    SearchResource.FACULTY: {
        "query_param": "q",
        "search_fields": ("title", "description", "college_name_snapshot"),
        "filter_fields": {
            "department": "str",
            "qualification": "str",
            "designation": "str",
            "specialization": "str",
            "location": "str",
            "employment_type": "str",
            "work_type": "str",
            "experience": "int",
            "salary_min": "decimal",
            "salary_max": "decimal",
        },
        "sort_fields": ("recent", "oldest", "salary_high", "salary_low", "title"),
        "default_sort": "recent",
    },
    SearchResource.COMPANIES: {
        "query_param": "q",
        "search_fields": (
            "name",
            "legal_name",
            "industry",
            "headquarters_location",
            "city",
        ),
        "filter_fields": {
            "verification_status": "str",
            "is_active": "bool",
            "industry": "str",
            "city": "str",
            "created_after": "date",
            "created_before": "date",
        },
        "sort_fields": (
            "name",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ),
        "default_sort": "name",
    },
    SearchResource.COLLEGES: {
        "query_param": "q",
        "search_fields": ("name", "city", "state", "country"),
        "filter_fields": {
            "verification_status": "str",
            "is_active": "bool",
            "city": "str",
            "state": "str",
            "created_after": "date",
            "created_before": "date",
        },
        "sort_fields": (
            "name",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ),
        "default_sort": "name",
    },
    SearchResource.APPLICATIONS: {
        "query_param": "q",
        "search_fields": (
            "applicant_name_snapshot",
            "job_title_snapshot",
            "company_name_snapshot",
            "vacancy_title_snapshot",
            "college_name_snapshot",
        ),
        "filter_fields": {
            "domain": "str",
            "status": "str",
            "company_id": "uuid",
            "college_id": "uuid",
            "job_posting_id": "uuid",
            "vacancy_id": "uuid",
            "created_after": "date",
            "created_before": "date",
        },
        "sort_fields": ("recent", "oldest", "status"),
        "default_sort": "recent",
    },
    SearchResource.INVOICES: {
        "query_param": "q",
        "search_fields": ("invoice_number", "bill_to_name_snapshot"),
        "filter_fields": {
            "domain": "str",
            "status": "str",
            "payment_status": "str",
            "issued_from": "date",
            "issued_to": "date",
            "amount_min": "decimal",
            "amount_max": "decimal",
        },
        "sort_fields": (
            "-created_at",
            "created_at",
            "-issued_at",
            "issued_at",
            "-total_amount",
            "total_amount",
        ),
        "default_sort": "-created_at",
    },
    SearchResource.GUARANTEES: {
        "query_param": "q",
        "search_fields": ("claim_number", "reason"),
        "filter_fields": {
            "domain": "str",
            "status": "str",
            "claim_type": "str",
            "submitted_from": "date",
            "submitted_to": "date",
        },
        "sort_fields": ("-submitted_at", "submitted_at", "-created_at", "created_at"),
        "default_sort": "-submitted_at",
    },
    SearchResource.JOB_SEEKERS: {
        "query_param": "q",
        "search_fields": (
            "first_name",
            "last_name",
            "headline",
            "summary",
            "current_location",
            "current_company",
        ),
        "filter_fields": {
            "profile_status": "str",
            "experience_min": "int",
            "experience_max": "int",
            "location": "str",
            "created_after": "date",
            "created_before": "date",
        },
        "sort_fields": (
            "name",
            "-created_at",
            "created_at",
            "experience_years",
            "-experience_years",
        ),
        "default_sort": "-created_at",
    },
    SearchResource.RECRUITERS: {
        "query_param": "q",
        "search_fields": (
            "first_name",
            "last_name",
            "department",
            "company_association",
            "designation",
        ),
        "filter_fields": {
            "profile_status": "str",
            "created_after": "date",
            "created_before": "date",
        },
        "sort_fields": ("name", "-created_at", "created_at"),
        "default_sort": "-created_at",
    },
    SearchResource.PROFESSORS: {
        "query_param": "q",
        "search_fields": (
            "first_name",
            "last_name",
            "specialization",
            "current_designation",
            "current_institution",
            "highest_qualification",
        ),
        "filter_fields": {
            "profile_status": "str",
            "specialization": "str",
            "experience_min": "int",
            "experience_max": "int",
            "created_after": "date",
            "created_before": "date",
        },
        "sort_fields": (
            "name",
            "-created_at",
            "created_at",
            "experience_years",
            "-experience_years",
        ),
        "default_sort": "-created_at",
    },
    SearchResource.ADMIN: {
        "query_param": "q",
        "search_fields": ("email",),
        "filter_fields": {
            "domain": "str",
            "resource": "str",
            "is_active": "bool",
            "account_status": "str",
        },
        "sort_fields": ("-created_at", "created_at", "email"),
        "default_sort": "-created_at",
    },
}


def get_resource_config(resource: str) -> dict:
    if resource in (SearchResource.VACANCIES, SearchResource.VACANCIES.value):
        resource = SearchResource.FACULTY.value
    for key, config in RESOURCE_CONFIG.items():
        if key == resource or getattr(key, "value", key) == resource:
            return config
    raise ValueError(f"Unknown search resource: {resource}")
