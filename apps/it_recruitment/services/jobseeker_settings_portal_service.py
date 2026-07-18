"""Job seeker Settings portal — Account & Security Center context."""

from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.authentication.services.connected_accounts_service import (
    ConnectedAccountsService,
)
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.account_settings_service import (
    AccountSettingsService,
    NOTIFICATION_FIELDS,
)


@dataclass
class SettingsPortalContext:
    account: dict
    notifications: dict
    privacy: dict
    security: dict
    sessions: list[dict]
    connected_accounts: list[dict]
    audit_log: list[dict]
    api_urls: dict


class JobSeekerSettingsPortalService(BaseService):
    NOTIFICATION_LABELS = {
        "notify_job_recommendations": "Job Recommendations",
        "notify_recruiter_messages": "Recruiter Messages",
        "notify_application_updates": "Application Updates",
        "notify_interviews": "Interview Notifications",
        "notify_offers": "Offer Notifications",
        "notify_marketing": "Marketing Emails",
        "notify_security_alerts": "Security Alerts",
        "notify_profile_views": "Profile View Notifications",
        "notify_resume_downloads": "Resume Download Notifications",
        "notify_weekly_digest": "Weekly Job Digest",
    }

    PRIVACY_LABELS = {
        "allow_recruiter_resume_download": "Allow Recruiters to Download Resume",
        "allow_recruiter_contact": "Allow Recruiters to Contact Me",
        "show_email_on_profile": "Show Email Address",
        "show_phone_on_profile": "Show Phone Number",
    }

    def __init__(self):
        self.account = AccountSettingsService()
        self.sessions = SessionManagementService()
        self.audit = SecurityAuditService()
        self.connected = ConnectedAccountsService()

    def build(self, profile: JobSeekerProfile, *, request) -> SettingsPortalContext:
        user = profile.user
        settings = self.account.get_or_create_settings(profile)
        current_key = self.sessions.current_session_key_from_request(request)
        pu = lambda name, **kw: PortalURLService.jobseeker(user, name, **kw)
        return SettingsPortalContext(
            account=self.account.build_account_info(profile),
            notifications=self.account.build_notification_prefs(settings),
            privacy=self.account.build_privacy_settings(profile, settings),
            security=self.account.build_security_summary(profile),
            sessions=self.sessions.list_sessions(
                domain=DomainType.IT,
                user_id=profile.user_id,
                current_session_key=current_key,
            ),
            connected_accounts=self.connected.list_for_user(
                domain=DomainType.IT,
                user_id=profile.user_id,
                settings_return_url=pu("jobseeker_settings"),
            ),
            audit_log=[
                self.audit.serialize_event(e)
                for e in self.audit.list_activity_for_user(
                    domain=DomainType.IT, user_id=profile.user_id, limit=15
                )
            ],
            api_urls={
                "account": pu("jobseeker_settings_account_api"),
                "password": pu("jobseeker_settings_password_api"),
                "notifications": pu("jobseeker_settings_notifications_api"),
                "privacy": pu("jobseeker_settings_privacy_api"),
                "sessions": pu("jobseeker_settings_sessions_api"),
                "revoke_others": pu("jobseeker_settings_revoke_sessions_api"),
                "connected": pu("jobseeker_settings_connected_api"),
                "delete_account": pu("jobseeker_settings_delete_api"),
                "audit": pu("jobseeker_settings_audit_api"),
            },
        )

    def notification_toggles(self, notifications: dict) -> list[dict]:
        return [
            {
                "key": key,
                "label": self.NOTIFICATION_LABELS[key],
                "enabled": notifications.get(key, False),
            }
            for key in NOTIFICATION_FIELDS
        ]

    def privacy_toggles(self, privacy: dict) -> list[dict]:
        from apps.it_recruitment.services.account_settings_service import PRIVACY_FIELDS

        return [
            {
                "key": key,
                "label": self.PRIVACY_LABELS[key],
                "enabled": privacy.get(key, False),
            }
            for key in PRIVACY_FIELDS
        ]
