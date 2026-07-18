from django.db import models


class ClaimType(models.TextChoices):
    REPLACEMENT = "replacement", "Replacement"
    REFUND = "refund", "Refund"
    PLATFORM_REVIEW = "platform_review", "Platform Review"


class ClaimStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    MORE_INFORMATION_REQUIRED = "more_information_required", "More Information Required"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    REFUND_PROCESSING = "refund_processing", "Refund Processing"
    REFUNDED = "refunded", "Refunded"
    REPLACEMENT_SEARCH = "replacement_search", "Replacement Search"
    REPLACEMENT_COMPLETED = "replacement_completed", "Replacement Completed"
    RESOLVED = "resolved", "Resolved"
    CANCELLED = "cancelled", "Cancelled"
    INVALID_DATA = "invalid_data", "Invalid Data (Orphaned)"
    ARCHIVED = "archived", "Archived"


class ClaimResolution(models.TextChoices):
    REFUND = "refund", "Refund"
    REPLACEMENT_CANDIDATE = "replacement_candidate", "Replacement Candidate"
    REJECTED = "rejected", "Rejected"


class GuaranteeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    CLAIMED = "claimed", "Claimed"
    CLOSED = "closed", "Closed"


class ExitReason(models.TextChoices):
    ABSCONDED = "absconded", "Candidate Absconded"
    RESIGNED = "resigned", "Candidate Resigned"
    DID_NOT_CONTINUE = "did_not_continue", "Candidate Did Not Continue"
    TERMINATED = "terminated", "Candidate Terminated"
    DID_NOT_JOIN = "did_not_join", "Candidate Did Not Join After Confirmation"
    PERFORMANCE_ISSUE = "performance_issue", "Performance Issue"
    BGV_FAILURE = "bgv_failure", "Background Verification Failure"
    OTHER = "other", "Other"


DEFAULT_GUARANTEE_DAYS = 90

class PlacementClaimReason(models.TextChoices):
    ABSCONDED = "absconded", "Absconded"
    LEFT_WITHOUT_NOTICE = "left_without_notice", "Left Without Notice"
    FAILED_TO_JOIN = "failed_to_join", "Failed to Join after Confirmed Joining"
    OTHER_REVIEW_REQUIRED = "other_review_required", "Other (Review Required)"

class PlacementClaimStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    MORE_INFORMATION_REQUIRED = "more_information_required", "More Information Required"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    REFUND_PENDING = "refund_pending", "Refund Pending"
    REFUND_PROCESSING = "refund_processing", "Refund Processing"
    REFUNDED = "refunded", "Refunded"
    REFUND_FAILED = "refund_failed", "Refund Failed"
    CLOSED = "closed", "Closed"
