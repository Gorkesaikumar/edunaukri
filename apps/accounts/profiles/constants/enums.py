from django.db import models


class ProfileType(models.TextChoices):
    JOB_SEEKER = "job_seeker", "Job Seeker"
    RECRUITER = "recruiter", "Recruiter"
    PROFESSOR = "professor", "Professor"
    COLLEGE = "college", "College"
    ADMIN = "admin", "Admin"


class ProfileStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DEACTIVATED = "deactivated", "Deactivated"


class ProfileVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    EMPLOYERS_ONLY = "employers_only", "Employers Only"


class EmploymentTypePreference(models.TextChoices):
    FULL_TIME = "full_time", "Full Time"
    PART_TIME = "part_time", "Part Time"
    CONTRACT = "contract", "Contract"


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    NON_BINARY = "non_binary", "Non-binary"
    PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"
    OTHER = "other", "Other"


class WorkModePreference(models.TextChoices):
    REMOTE = "remote", "Remote"
    HYBRID = "hybrid", "Hybrid"
    ONSITE = "onsite", "On-site"


# Fields hidden on public profile views regardless of visibility setting.
PRIVATE_PROFILE_FIELDS = frozenset(
    {
        "phone",
        "official_email",
        "contact_phone",
        "contact_email",
        "current_salary",
        "expected_salary",
        "notice_period_days",
        "created_by_id",
        "updated_by_id",
        "deleted_by_id",
        "is_deleted",
        "deleted_at",
        "verification_status",
        "profile_status",
    }
)
