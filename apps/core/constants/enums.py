from django.db import models


class DomainType(models.TextChoices):
    IT = "it", "IT Recruitment"
    FACULTY = "faculty", "Faculty Recruitment"
    PLATFORM = "platform", "Platform"


class ActorType(models.TextChoices):
    ADMIN = "admin", "Admin"
    IT_USER = "it_user", "IT User"
    PROFESSOR = "professor", "Professor"
    COLLEGE = "college", "College"
    SYSTEM = "system", "System"


class EntityReferenceType(models.TextChoices):
    IT_JOB_APPLICATION = "it_job_application", "IT Job Application"
    FACULTY_APPLICATION = "faculty_application", "Faculty Application"
    IT_JOB_POSTING = "it_job_posting", "IT Job Posting"
    FACULTY_VACANCY = "faculty_vacancy", "Faculty Vacancy"
    IT_COMPANY = "it_company", "IT Company"
    FACULTY_COLLEGE = "faculty_college", "Faculty College"
    STORED_FILE = "stored_file", "Stored File"


class RecordStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    ARCHIVED = "archived", "Archived"


class PlatformRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    JOB_SEEKER = "job_seeker", "Job Seeker"
    RECRUITER = "recruiter", "Recruiter"
    PROFESSOR = "professor", "Professor"
    COLLEGE = "college", "College"


class ApplicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    SHORTLISTED = "shortlisted", "Shortlisted"
    INTERVIEW = "interview", "Interview"
    OFFERED = "offered", "Offered"
    PLACED = "placed", "Placed"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ISSUED = "issued", "Issued"
    PAID = "paid", "Paid"
    OVERDUE = "overdue", "Overdue"
    CANCELLED = "cancelled", "Cancelled"


class GuaranteeStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CLOSED = "closed", "Closed"


class DocumentType(models.TextChoices):
    RESUME = "resume", "Resume"
    CV = "cv", "CV"
    CERTIFICATE = "certificate", "Certificate"
    LOGO = "logo", "Logo"
    INVOICE = "invoice", "Invoice"
    CLAIM = "claim", "Claim Document"
    EXPORT = "export", "Export"
    OTHER = "other", "Other"


class OrganizationStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    DEACTIVATED = 'deactivated', 'Deactivated'
    SUSPENDED = 'suspended', 'Suspended'
    BLOCKED = 'blocked', 'Blocked'
