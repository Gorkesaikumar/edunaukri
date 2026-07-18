from django.db import models


class TestimonialDomain(models.TextChoices):
    """Recruitment domain a placement testimonial belongs to."""

    IT = "it", "IT Placement"
    FACULTY = "faculty", "Faculty Placement"


class TestimonialVisibility(models.TextChoices):
    """Public visibility of a testimonial."""

    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"


class ActivityDomain(models.TextChoices):
    """Recruitment domain a platform activity belongs to."""

    IT = "it", "IT"
    FACULTY = "faculty", "Faculty"


class ActivityType(models.TextChoices):
    """Kinds of live hiring activity shown in the public feed."""

    JOB_POSTED = "job_posted", "Job Posted"
    FACULTY_POSTED = "faculty_posted", "Faculty Vacancy Posted"
    CANDIDATE_APPLIED = "candidate_applied", "Candidate Applied"
    SHORTLISTED = "shortlisted", "Candidate Shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled", "Interview Scheduled"
    OFFER_RELEASED = "offer_released", "Offer Released"
    CANDIDATE_HIRED = "candidate_hired", "Candidate Hired"
    RECRUITER_VERIFIED = "recruiter_verified", "Recruiter Verified"
    COMPANY_JOINED = "company_joined", "Company Joined"
    UNIVERSITY_JOINED = "university_joined", "University Joined"
