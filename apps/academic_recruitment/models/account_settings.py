"""Account settings — notifications, privacy, security metadata."""

from django.db import models

from apps.core.models.base import AuditedBaseModel


class ProfessorAccountSettings(AuditedBaseModel):
    """Per-professor notification, privacy, and security preferences."""

    professor = models.OneToOneField(
        "academic_recruitment.ProfessorProfile",
        on_delete=models.CASCADE,
        related_name="account_settings",
    )
    notify_vacancy_recommendations = models.BooleanField(default=True)
    notify_institution_messages = models.BooleanField(default=True)
    notify_application_updates = models.BooleanField(default=True)
    notify_interviews = models.BooleanField(default=True)
    notify_offers = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    notify_security_alerts = models.BooleanField(default=True)
    notify_profile_views = models.BooleanField(default=True)
    notify_cv_downloads = models.BooleanField(default=True)
    notify_weekly_digest = models.BooleanField(default=True)
    allow_institution_cv_download = models.BooleanField(default=True)
    allow_institution_contact = models.BooleanField(default=True)
    show_email_on_profile = models.BooleanField(default=False)
    show_phone_on_profile = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "faculty_professor_account_settings"

    @classmethod
    def defaults(cls) -> dict:
        return {
            "notify_vacancy_recommendations": True,
            "notify_institution_messages": True,
            "notify_application_updates": True,
            "notify_interviews": True,
            "notify_offers": True,
            "notify_marketing": False,
            "notify_security_alerts": True,
            "notify_profile_views": True,
            "notify_cv_downloads": True,
            "notify_weekly_digest": True,
            "allow_institution_cv_download": True,
            "allow_institution_contact": True,
            "show_email_on_profile": False,
            "show_phone_on_profile": False,
            "phone_verified": False,
        }


class CollegeAccountSettings(AuditedBaseModel):
    """Per institution recruiter notification, contact, and security preferences."""

    college_user = models.OneToOneField(
        "accounts.CollegeUser",
        on_delete=models.CASCADE,
        related_name="account_settings",
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    notify_new_applications = models.BooleanField(default=True)
    notify_application_updates = models.BooleanField(default=True)
    notify_interviews = models.BooleanField(default=True)
    notify_offers = models.BooleanField(default=True)
    notify_vacancy_updates = models.BooleanField(default=True)
    notify_verification_alerts = models.BooleanField(default=True)
    notify_faculty_messages = models.BooleanField(default=True)
    notify_marketing = models.BooleanField(default=False)
    notify_security_alerts = models.BooleanField(default=True)
    notify_weekly_digest = models.BooleanField(default=True)
    show_email_to_applicants = models.BooleanField(default=False)
    show_phone_to_applicants = models.BooleanField(default=False)
    allow_direct_applicant_contact = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)

    class Meta:
        db_table = "faculty_college_account_settings"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @classmethod
    def defaults(cls) -> dict:
        return {
            "notify_new_applications": True,
            "notify_application_updates": True,
            "notify_interviews": True,
            "notify_offers": True,
            "notify_vacancy_updates": True,
            "notify_verification_alerts": True,
            "notify_faculty_messages": True,
            "notify_marketing": False,
            "notify_security_alerts": True,
            "notify_weekly_digest": True,
            "show_email_to_applicants": False,
            "show_phone_to_applicants": False,
            "allow_direct_applicant_contact": True,
            "phone_verified": False,
        }
