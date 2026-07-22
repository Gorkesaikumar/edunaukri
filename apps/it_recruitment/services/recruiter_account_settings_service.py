"""Recruiter account settings — account info, notifications, deletion."""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.profiles.constants.enums import ProfileStatus
from apps.authentication.models import LoginAttempt
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterAccountSettings, RecruiterProfile

RECRUITER_NOTIFICATION_FIELDS = (
    "notify_new_applications",
    "notify_interview_updates",
    "notify_candidate_messages",
    "notify_marketing",
    "notify_security_alerts",
)


class RecruiterAccountSettingsService(BaseService):
    NOTIFICATION_LABELS = {
        "notify_new_applications": "New Candidate Applications",
        "notify_interview_updates": "Interview Updates",
        "notify_candidate_messages": "Candidate Messages",
        "notify_marketing": "Marketing Emails",
        "notify_security_alerts": "Security Alerts",
    }

    def __init__(self):
        self.audit = SecurityAuditService()
        self.sessions = SessionManagementService()

    def get_or_create_settings(
        self, profile: RecruiterProfile
    ) -> RecruiterAccountSettings:
        settings, created = RecruiterAccountSettings.objects.get_or_create(
            recruiter=profile,
            defaults=RecruiterAccountSettings.defaults(),
        )
        if created:
            settings.created_by_id = profile.user_id
            settings.save(update_fields=["created_by_id"])
        return settings

    @BaseService.atomic
    def update_account_info(
        self, profile: RecruiterProfile, data: dict, *, actor_id, request_meta: dict
    ) -> dict:
        if "first_name" in data:
            first = (data.get("first_name") or "").strip()
            if not first:
                raise ValidationException("First name is required.")
            profile.first_name = first
        if "last_name" in data:
            profile.last_name = (data.get("last_name") or "").strip()
        if "phone" in data:
            profile.phone = (data.get("phone") or "").strip()
        if "official_email" in data:
            profile.official_email = (data.get("official_email") or "").strip()
        if "designation" in data:
            profile.designation = (data.get("designation") or "").strip()
        profile.save(
            update_fields=[
                "first_name",
                "last_name",
                "phone",
                "official_email",
                "designation",
                "updated_at",
            ]
        )
        if "phone" in data:
            settings = self.get_or_create_settings(profile)
            settings.phone_verified = False
            settings.save(update_fields=["phone_verified", "updated_at"])
            self.audit.record(
                domain=DomainType.IT,
                user_id=profile.user_id,
                event_type="phone.updated",
                title="Phone number updated",
                description="Your mobile number was updated.",
                ip_address=request_meta.get("ip_address"),
            )
        return self.build_account_info(profile)

    @BaseService.atomic
    def update_notifications(self, profile: RecruiterProfile, data: dict) -> dict:
        settings = self.get_or_create_settings(profile)
        for field in RECRUITER_NOTIFICATION_FIELDS:
            if field in data:
                setattr(settings, field, bool(data[field]))
        settings.save()
        return self.build_notification_prefs(settings)

    @BaseService.atomic
    def delete_account(
        self, profile: RecruiterProfile, *, password: str, actor_id, request_meta: dict
    ) -> None:
        user = profile.user
        if not user.check_password(password):
            raise ValidationException("Password confirmation is incorrect.")
        self.sessions.revoke_other_sessions(domain=DomainType.IT, user_id=user.pk)
        profile.profile_status = ProfileStatus.DEACTIVATED
        profile.is_deleted = True
        profile.deleted_at = timezone.now()
        profile.deleted_by_id = actor_id
        profile.save(
            update_fields=[
                "profile_status",
                "is_deleted",
                "deleted_at",
                "deleted_by_id",
                "updated_at",
            ]
        )
        user.is_active = False
        user.account_status = AccountStatus.DEACTIVATED
        user.is_deleted = True
        user.deleted_at = timezone.now()
        user.save(
            update_fields=[
                "is_active",
                "account_status",
                "is_deleted",
                "deleted_at",
                "updated_at",
            ]
        )
        self.audit.record(
            domain=DomainType.IT,
            user_id=user.pk,
            event_type="account.deleted",
            title="Account deletion requested",
            description="Your recruiter account was deactivated and scheduled for removal.",
            ip_address=request_meta.get("ip_address"),
        )

    def build_account_info(self, profile: RecruiterProfile) -> dict:
        user = profile.user
        settings = self.get_or_create_settings(profile)
        attempt = (
            LoginAttempt.objects.filter(
                domain=DomainType.IT, user_id=user.pk, result="success"
            )
            .order_by("-attempted_at")
            .first()
        )
        return {
            "full_name": profile.full_name,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": user.email,
            "official_email": profile.official_email,
            "phone": profile.phone,
            "designation": profile.designation,
            "company_association": profile.company_association,
            "username": user.email.split("@")[0],
            "registered_at": user.created_at.isoformat(),
            "registered_label": timezone.localtime(user.created_at).strftime(
                "%b %d, %Y"
            ),
            "last_login_label": timezone.localtime(attempt.attempted_at).strftime(
                "%b %d, %Y · %I:%M %p"
            )
            if attempt
            else "—",
            "account_status": user.account_status,
            "account_status_label": user.get_account_status_display()
            if hasattr(user, "get_account_status_display")
            else user.account_status.replace("_", " ").title(),
            "email_verified": user.email_verified,
            "phone_verified": settings.phone_verified,
        }

    @staticmethod
    def build_notification_prefs(settings: RecruiterAccountSettings) -> dict:
        return {
            field: getattr(settings, field) for field in RECRUITER_NOTIFICATION_FIELDS
        }

    def build_security_summary(self, profile: RecruiterProfile) -> dict:
        user = profile.user
        settings = self.get_or_create_settings(profile)
        attempt = (
            LoginAttempt.objects.filter(
                domain=DomainType.IT, user_id=user.pk, result="success"
            )
            .order_by("-attempted_at")
            .first()
        )
        recommendations = []
        if not user.email_verified:
            recommendations.append("Verify your email address.")
        if profile.phone and not settings.phone_verified:
            recommendations.append("Verify your mobile number.")
        if not settings.password_changed_at:
            recommendations.append("Update your password regularly.")
        if not profile.company_association:
            recommendations.append(
                "Add your company association to build trust with candidates."
            )
        return {
            "password_changed_label": timezone.localtime(
                settings.password_changed_at
            ).strftime("%b %d, %Y")
            if settings.password_changed_at
            else "Never changed",
            "last_login_label": timezone.localtime(attempt.attempted_at).strftime(
                "%b %d, %Y · %I:%M %p"
            )
            if attempt
            else "—",
            "failed_login_attempts": user.failed_login_attempts,
            "security_status": "Good"
            if user.email_verified and settings.password_changed_at
            else "Needs attention",
            "recommendations": recommendations,
        }

    def notification_toggles(self, notifications: dict) -> list[dict]:
        return [
            {
                "key": key,
                "label": self.NOTIFICATION_LABELS[key],
                "enabled": notifications.get(key, False),
            }
            for key in RECRUITER_NOTIFICATION_FIELDS
        ]
