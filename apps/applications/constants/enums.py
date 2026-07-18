"""Status enums and constants for the Job Application Management module (IT domain)."""

from django.db import models


class JobApplicationStatus(models.TextChoices):
    APPLIED = "applied", "Applied"
    UNDER_REVIEW = "under_review", "Under Review"
    SHORTLISTED = "shortlisted", "Shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
    INTERVIEW_COMPLETED = "interview_completed", "Interview Completed"
    OFFER_RELEASED = "offer_released", "Offer Released"
    OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
    OFFER_DECLINED = "offer_declined", "Offer Declined"
    SELECTED = "selected", "Selected"
    JOINING_IN_PROGRESS = "joining_in_progress", "Joining in Progress"
    JOINED = "joined", "Joined"
    HIRED = "hired", "Hired"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    EXPIRED = "expired", "Expired"


class ApplicationSource(models.TextChoices):
    DIRECT = "direct", "Direct"
    REFERRAL = "referral", "Referral"
    JOB_BOARD = "job_board", "Job Board"
    AGENCY = "agency", "Agency"
    CAREER_FAIR = "career_fair", "Career Fair"
    INTERNAL = "internal", "Internal"
    OTHER = "other", "Other"


class TimelineEventType(models.TextChoices):
    CREATED = "created", "Application Created"
    STATUS_CHANGED = "status_changed", "Status Changed"
    RECRUITER_COMMENT = "recruiter_comment", "Recruiter Comment"
    CANDIDATE_ACTION = "candidate_action", "Candidate Action"
    WITHDRAW = "withdraw", "Withdraw"
    OFFER = "offer", "Offer"
    HIRE = "hire", "Hire"
    REJECT = "reject", "Reject"


# Terminal statuses — no further recruiter-driven transitions.
TERMINAL_STATUSES = frozenset(
    {
        JobApplicationStatus.JOINED,
        JobApplicationStatus.HIRED,
        JobApplicationStatus.REJECTED,
        JobApplicationStatus.WITHDRAWN,
        JobApplicationStatus.EXPIRED,
        JobApplicationStatus.OFFER_DECLINED,
    }
)

# Legacy status values migrated from the Phase-1 implementation.
LEGACY_STATUS_MAP = {
    "submitted": JobApplicationStatus.APPLIED,
    "interview": JobApplicationStatus.INTERVIEW_SCHEDULED,
    "offered": JobApplicationStatus.OFFER_RELEASED,
    "placed": JobApplicationStatus.JOINED,
}
