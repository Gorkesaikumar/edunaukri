"""Status enums and constants for the College / Institution Management module."""

from django.db import models


class InstitutionType(models.TextChoices):
    """Academic classification of the institution."""

    ENGINEERING = "engineering", "Engineering College"
    ARTS_SCIENCE = "arts_science", "Arts & Science College"
    MEDICAL = "medical", "Medical College"
    LAW = "law", "Law College"
    MANAGEMENT = "management", "Management Institute"
    POLYTECHNIC = "polytechnic", "Polytechnic"
    UNIVERSITY = "university", "University"
    DEEMED_UNIVERSITY = "deemed_university", "Deemed University"
    RESEARCH_INSTITUTE = "research_institute", "Research Institute"
    OTHER = "other", "Other"


class OwnershipType(models.TextChoices):
    """Ownership / funding classification."""

    GOVERNMENT = "government", "Government"
    PRIVATE = "private", "Private"
    AIDED = "aided", "Government Aided"
    AUTONOMOUS = "autonomous", "Autonomous"
    DEEMED = "deemed", "Deemed"
    PUBLIC_PRIVATE = "public_private", "Public-Private Partnership"
    OTHER = "other", "Other"


class CollegeMemberRole(models.TextChoices):
    """Role of a college user within an institution."""

    OWNER = "owner", "Owner"
    ADMIN = "admin", "Administrator"
    MEMBER = "member", "Member"


class InstitutionVerificationStatus(models.TextChoices):
    """Verification lifecycle for institution onboarding and trust."""

    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class InstitutionDocumentType(models.TextChoices):
    """Categories of institution documents."""

    APPROVAL_CERTIFICATE = "approval_certificate", "Approval Certificate"
    ACCREDITATION_CERTIFICATE = "accreditation_certificate", "Accreditation Certificate"
    NAAC_DOCUMENT = "naac_document", "NAAC Document"
    AICTE_DOCUMENT = "aicte_document", "AICTE Document"
    UGC_DOCUMENT = "ugc_document", "UGC Document"
    BROCHURE = "brochure", "Institution Brochure"
    LOGO = "logo", "Logo"
    CAMPUS_IMAGE = "campus_image", "Campus Image"
    OTHER = "other", "Other"
