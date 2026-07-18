"""Status enums and constants for the Faculty Vacancy Management module."""

from django.db import models


class VacancyStatus(models.TextChoices):
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
    VISITING = "visiting", "Visiting"
    ADJUNCT = "adjunct", "Adjunct"
    TENURE_TRACK = "tenure_track", "Tenure Track"


class WorkType(models.TextChoices):
    ONSITE = "onsite", "Onsite"
    HYBRID = "hybrid", "Hybrid"
    REMOTE = "remote", "Remote Teaching"


class Designation(models.TextChoices):
    PROFESSOR = "professor", "Professor"
    ASSOCIATE_PROFESSOR = "associate_professor", "Associate Professor"
    ASSISTANT_PROFESSOR = "assistant_professor", "Assistant Professor"
    LECTURER = "lecturer", "Lecturer"
    SENIOR_LECTURER = "senior_lecturer", "Senior Lecturer"
    HEAD_OF_DEPARTMENT = "head_of_department", "Head of Department"
    DEAN = "dean", "Dean"
    RESEARCH_FELLOW = "research_fellow", "Research Fellow"
    VISITING_FACULTY = "visiting_faculty", "Visiting Faculty"


class QualificationLevel(models.TextChoices):
    BACHELORS = "bachelors", "Bachelor's"
    MASTERS = "masters", "Master's"
    MPHIL = "mphil", "M.Phil"
    PHD = "phd", "Ph.D"
    POSTDOC = "postdoc", "Post-Doctoral"


class RecruitmentCategory(models.TextChoices):
    REGULAR = "regular", "Regular"
    CONTRACTUAL = "contractual", "Contractual"
    GUEST = "guest", "Guest"
    DEPUTATION = "deputation", "Deputation"
    AD_HOC = "ad_hoc", "Ad Hoc"


class SalaryVisibility(models.TextChoices):
    VISIBLE = "visible", "Visible"
    HIDDEN = "hidden", "Hidden"
    ON_REQUEST = "on_request", "On Request"


class VacancyVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    INTERNAL = "internal", "Internal"


# Statuses that are considered publicly discoverable.
PUBLIC_STATUSES = (VacancyStatus.PUBLISHED,)

# Statuses from which a vacancy may transition to PUBLISHED.
PUBLISHABLE_STATUSES = (
    VacancyStatus.DRAFT,
    VacancyStatus.PENDING_APPROVAL,
    VacancyStatus.PAUSED,
)
