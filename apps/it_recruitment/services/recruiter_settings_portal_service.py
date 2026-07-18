"""Recruiter Settings portal — Account & Security Center context."""

from __future__ import annotations

from dataclasses import dataclass

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
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.recruiter_account_settings_service import (
    RecruiterAccountSettingsService,
)


@dataclass
class RecruiterSettingsPortalContext:
    account: dict
    notifications: dict
    security: dict
    sessions: list[dict]
    connected_accounts: list[dict]
    audit_log: list[dict]
    api_urls: dict


class RecruiterSettingsPortalService(BaseService):
    def __init__(self):
        self.account = RecruiterAccountSettingsService()
        self.sessions = SessionManagementService()
        self.audit = SecurityAuditService()
        self.connected = ConnectedAccountsService()

    def build(
        self, profile: RecruiterProfile, *, request
    ) -> RecruiterSettingsPortalContext:
        user = profile.user
        settings = self.account.get_or_create_settings(profile)
        current_key = self.sessions.current_session_key_from_request(request)
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        return RecruiterSettingsPortalContext(
            account=self.account.build_account_info(profile),
            notifications=self.account.build_notification_prefs(settings),
            security=self.account.build_security_summary(profile),
            sessions=self.sessions.list_sessions(
                domain=DomainType.IT,
                user_id=profile.user_id,
                current_session_key=current_key,
            ),
            connected_accounts=self.connected.list_for_user(
                domain=DomainType.IT,
                user_id=profile.user_id,
                settings_return_url=pu("recruiter_settings"),
            ),
            audit_log=[
                self.audit.serialize_event(e)
                for e in self.audit.list_activity_for_user(
                    domain=DomainType.IT, user_id=profile.user_id, limit=15
                )
            ],
            api_urls={
                "account": pu("recruiter_settings_account_api"),
                "password": pu("recruiter_settings_password_api"),
                "notifications": pu("recruiter_settings_notifications_api"),
                "sessions": pu("recruiter_settings_sessions_api"),
                "revoke_others": pu("recruiter_settings_revoke_sessions_api"),
                "connected": pu("recruiter_settings_connected_api"),
                "delete_account": pu("recruiter_settings_delete_api"),
                "audit": pu("recruiter_settings_audit_api"),
            },
        )

    def notification_toggles(self, notifications: dict) -> list[dict]:
        return self.account.notification_toggles(notifications)
