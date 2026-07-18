"""Status enums and constants for the Company Management module (IT domain)."""

from django.db import models


class OrganizationType(models.TextChoices):
    """Legal / structural classification of a company."""

    PRIVATE_LIMITED = "private_limited", "Private Limited"
    PUBLIC_LIMITED = "public_limited", "Public Limited"
    STARTUP = "startup", "Startup"
    MNC = "mnc", "MNC"
    GOVERNMENT = "government", "Government"
    NGO = "ngo", "NGO / Non-Profit"
    PARTNERSHIP = "partnership", "Partnership"
    PROPRIETORSHIP = "proprietorship", "Proprietorship"
    LLP = "llp", "LLP"
    OTHER = "other", "Other"


class CompanySize(models.TextChoices):
    """Head-count band of the organization."""

    SIZE_1_10 = "1-10", "1-10 employees"
    SIZE_11_50 = "11-50", "11-50 employees"
    SIZE_51_200 = "51-200", "51-200 employees"
    SIZE_201_500 = "201-500", "201-500 employees"
    SIZE_501_1000 = "501-1000", "501-1000 employees"
    SIZE_1001_5000 = "1001-5000", "1001-5000 employees"
    SIZE_5000_PLUS = "5000+", "5000+ employees"


class CompanyMemberRole(models.TextChoices):
    """Role of a recruiter within a company."""

    OWNER = "owner", "Owner"
    ADMIN = "admin", "Admin"
    RECRUITER = "recruiter", "Recruiter"


class CompanyVerificationStatus(models.TextChoices):
    """Trust and moderation lifecycle for employer companies."""

    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"
