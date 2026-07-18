from django.db import models


class StorageFileType(models.TextChoices):
    RESUME = "resume", "Resume"
    CV = "cv", "CV"
    CERTIFICATE = "certificate", "Certificate"
    PROFILE_PHOTO = "profile_photo", "Profile Photo"
    COMPANY_LOGO = "company_logo", "Company Logo"
    COLLEGE_LOGO = "college_logo", "College Logo"
    COLLEGE_BANNER = "college_banner", "College Banner"
    INVOICE_PDF = "invoice_pdf", "Invoice PDF"
    CLAIM_DOCUMENT = "claim_document", "Claim Document"
    OTHER = "other", "Other"


class StorageFileStatus(models.TextChoices):
    UPLOADING = "uploading", "Uploading"
    ACTIVE = "active", "Active"
    QUARANTINED = "quarantined", "Quarantined"
    DELETED = "deleted", "Deleted"


class StorageBackendType(models.TextChoices):
    LOCAL = "local", "Local Filesystem"
    S3 = "s3", "Amazon S3"
