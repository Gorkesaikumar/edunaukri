"""Allowed IT job application status transitions (enterprise workflow)."""

ALLOWED_IT_TRANSITIONS = {
    None: {"applied"},
    "applied": {"under_review", "rejected", "withdrawn", "expired"},
    "under_review": {"shortlisted", "rejected", "withdrawn"},
    "shortlisted": {"interview_scheduled", "rejected", "withdrawn"},
    "interview_scheduled": {"interview_completed", "rejected", "withdrawn"},
    "interview_completed": {"selected", "rejected", "withdrawn"},
    "selected": {"joining_in_progress", "rejected", "withdrawn"},
    "joining_in_progress": {"joined", "rejected", "withdrawn"},
    "joined": set(),
    "hired": set(),
    "rejected": set(),
    "withdrawn": set(),
    "expired": set(),
}

# Enterprise faculty application workflow (Academic Recruitment domain).
ALLOWED_FACULTY_TRANSITIONS = {
    None: {"applied"},
    "applied": {"under_review", "shortlisted", "rejected", "withdrawn", "expired"},
    "under_review": {"shortlisted", "academic_verification", "rejected", "withdrawn"},
    "shortlisted": {"interview_scheduled", "rejected", "withdrawn"},
    "academic_verification": {"department_review", "rejected", "withdrawn"},
    "department_review": {"principal_review", "rejected", "withdrawn"},
    "principal_review": {"management_approval", "rejected", "withdrawn"},
    "management_approval": {"interview_scheduled", "rejected", "withdrawn"},
    "interview_scheduled": {
        "management_approval",
        "shortlisted",
        "interview_completed",
        "rejected",
        "withdrawn",
    },
    "interview_completed": {"selected", "rejected", "withdrawn"},
    "selected": {"joining_in_progress", "rejected", "withdrawn"},
    "joining_in_progress": {"joined", "rejected", "withdrawn"},
    "joined": set(),
    "rejected": set(),
    "withdrawn": set(),
    "expired": set(),
}
