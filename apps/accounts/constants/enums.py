from django.db import models


class AccountStatus(models.TextChoices):
    PENDING_VERIFICATION = "pending_verification", "Pending Verification"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DEACTIVATED = "deactivated", "Deactivated"


class ITUserRoleType(models.TextChoices):
    JOB_SEEKER = "job_seeker", "Job Seeker"
    RECRUITER = "recruiter", "Recruiter"
