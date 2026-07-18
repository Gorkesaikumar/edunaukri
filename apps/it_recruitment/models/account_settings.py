"""Job seeker account settings — notifications, privacy, security metadata."""

from django.db import models

from apps.core.models.base import AuditedBaseModel


class JobSeekerAccountSettings(AuditedBaseModel):
    """Per-seeker notification, privacy, and security preferences."""

    job_seeker = models.OneToOneField(
        "it_recruitment.JobSeekerProfile",
        on_delete=models.CASCADE,
        related_name="account_settings",
    )
    # Notification preferences
    notify_job_recommendations = models.BooleanField(default=True)
    notify_recruiter_messages = models.BooleanField(default=True)
    notify_application_updates = models.BooleanField(default=True)
    notify_interviews = models.BooleanField(default=True)
    notify_offers = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    notify_security_alerts = models.BooleanField(default=True)
    notify_profile_views = models.BooleanField(default=True)
    notify_resume_downloads = models.BooleanField(default=True)
    notify_weekly_digest = models.BooleanField(default=True)
    # Privacy controls (profile_visibility lives on JobSeekerProfile)
    allow_recruiter_resume_download = models.BooleanField(default=True)
    allow_recruiter_contact = models.BooleanField(default=True)
    show_email_on_profile = models.BooleanField(default=False)
    show_phone_on_profile = models.BooleanField(default=False)
    # Security metadata
    password_changed_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "it_job_seeker_account_settings"

    @classmethod
    def defaults(cls) -> dict:
        return {
            "notify_job_recommendations": True,
            "notify_recruiter_messages": True,
            "notify_application_updates": True,
            "notify_interviews": True,
            "notify_offers": True,
            "notify_marketing": False,
            "notify_security_alerts": True,
            "notify_profile_views": True,
            "notify_resume_downloads": True,
            "notify_weekly_digest": True,
            "allow_recruiter_resume_download": True,
            "allow_recruiter_contact": True,
            "show_email_on_profile": False,
            "show_phone_on_profile": False,
            "phone_verified": False,
        }


class RecruiterAccountSettings(AuditedBaseModel):
    """Per-recruiter notification and security preferences."""

    recruiter = models.OneToOneField(
        "it_recruitment.RecruiterProfile",
        on_delete=models.CASCADE,
        related_name="account_settings",
    )
    notify_new_applications = models.BooleanField(default=True)
    notify_interview_updates = models.BooleanField(default=True)
    notify_candidate_messages = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    notify_security_alerts = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "it_recruiter_account_settings"

    @classmethod
    def defaults(cls) -> dict:
        return {
            "notify_new_applications": True,
            "notify_interview_updates": True,
            "notify_candidate_messages": True,
            "notify_marketing": False,
            "notify_security_alerts": True,
            "phone_verified": False,
        }
