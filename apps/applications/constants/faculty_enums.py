"""Status enums and constants for the Faculty Application Management module."""

from django.db import models


class FacultyApplicationStatus(models.TextChoices):
    APPLIED = "applied", "Applied"
    UNDER_REVIEW = "under_review", "Application Under Review"
    SHORTLISTED = "shortlisted", "Shortlisted"
    ACADEMIC_VERIFICATION = "academic_verification", "Academic Verification"
    DEPARTMENT_REVIEW = "department_review", "Department Review"
    PRINCIPAL_REVIEW = "principal_review", "Principal Review"
    MANAGEMENT_APPROVAL = "management_approval", "Management Approval"
    INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
    INTERVIEW_COMPLETED = "interview_completed", "Interview Completed"
    OFFER_RELEASED = "offer_released", "Offer Released"
    OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
    OFFER_DECLINED = "offer_declined", "Offer Declined"
    SELECTED = "selected", "Selected"
    JOINING_IN_PROGRESS = "joining_in_progress", "Joining in Progress"
    JOINED = "joined", "Joined"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    EXPIRED = "expired", "Expired"


class FacultyTimelineEventType(models.TextChoices):
    CREATED = "created", "Application Created"
    STATUS_CHANGED = "status_changed", "Status Changed"
    COLLEGE_COMMENT = "college_comment", "College Comment"
    PROFESSOR_ACTION = "professor_action", "Professor Action"
    WITHDRAW = "withdraw", "Withdraw"
    OFFER = "offer", "Offer"
    JOINED = "joined", "Joined"
    REJECT = "reject", "Reject"


FACULTY_TERMINAL_STATUSES = frozenset(
    {
        FacultyApplicationStatus.JOINED,
        FacultyApplicationStatus.REJECTED,
        FacultyApplicationStatus.WITHDRAWN,
        FacultyApplicationStatus.EXPIRED,
        FacultyApplicationStatus.OFFER_DECLINED,
    }
)

FACULTY_LEGACY_STATUS_MAP = {
    "submitted": FacultyApplicationStatus.APPLIED,
    "shortlisted": FacultyApplicationStatus.SHORTLISTED,
    "interview": FacultyApplicationStatus.INTERVIEW_SCHEDULED,
    "offered": FacultyApplicationStatus.OFFER_RELEASED,
    "placed": FacultyApplicationStatus.JOINED,
}
