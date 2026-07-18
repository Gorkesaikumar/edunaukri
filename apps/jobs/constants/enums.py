"""Status enums and constants for the Job Management module (IT domain)."""

from django.db import models


class JobStatus(models.TextChoices):
    """Lifecycle status of a job posting."""

    DRAFT = "draft", "Draft"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    PUBLISHED = "published", "Published"
    PAUSED = "paused", "Paused"
    CLOSED = "closed", "Closed"
    EXPIRED = "expired", "Expired"
    ARCHIVED = "archived", "Archived"
    REJECTED = "rejected", "Rejected"


class EmploymentType(models.TextChoices):
    FULL_TIME = "full_time", "Full Time"
    PART_TIME = "part_time", "Part Time"
    CONTRACT = "contract", "Contract"
    INTERNSHIP = "internship", "Internship"
    TEMPORARY = "temporary", "Temporary"
    FREELANCE = "freelance", "Freelance"


class WorkMode(models.TextChoices):
    ONSITE = "onsite", "Onsite"
    REMOTE = "remote", "Remote"
    HYBRID = "hybrid", "Hybrid"


class SalaryVisibility(models.TextChoices):
    VISIBLE = "visible", "Visible"
    HIDDEN = "hidden", "Hidden"
    ON_REQUEST = "on_request", "On Request"


class JobVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    INTERNAL = "internal", "Internal"


# Statuses that are considered publicly discoverable / active.
PUBLIC_STATUSES = (JobStatus.PUBLISHED,)

# Statuses from which a job may transition to PUBLISHED.
PUBLISHABLE_STATUSES = (JobStatus.DRAFT, JobStatus.PENDING_APPROVAL, JobStatus.PAUSED)
