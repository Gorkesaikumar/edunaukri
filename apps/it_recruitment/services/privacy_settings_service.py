"""Update job seeker privacy settings with audit trail and real-time sync."""

from __future__ import annotations

from apps.accounts.profiles.constants.enums import ProfileVisibility
from apps.authentication.services.security_audit_service import SecurityAuditService
from apps.core.constants.enums import DomainType
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.services.account_settings_service import (
    AccountSettingsService,
    PRIVACY_FIELDS,
)
from apps.it_recruitment.services.jobseeker_privacy_service import (
    PRIVACY_FIELD_LABELS,
    PRIVACY_SUCCESS_MESSAGES,
    JobSeekerPrivacyService,
)
from apps.it_recruitment.services.privacy_sync_service import PrivacySyncService


class PrivacySettingsService(BaseService):
    """Persist privacy preferences, audit changes, and trigger platform sync."""

    def __init__(self):
        self.account = AccountSettingsService()
        self.audit = SecurityAuditService()
        self.sync = PrivacySyncService()
        self.privacy = JobSeekerPrivacyService()

    @BaseService.atomic
    def update(
        self, profile: JobSeekerProfile, data: dict, *, request_meta: dict
    ) -> dict:
        if not data:
            raise ValidationException("No privacy fields provided.")

        settings = self.account.get_or_create_settings(profile)
        changed: list[tuple[str, object, object]] = []

        visibility = data.get("profile_visibility")
        if visibility is not None:
            if visibility not in ProfileVisibility.values:
                raise ValidationException("Invalid profile visibility value.")
            old_visibility = profile.profile_visibility
            if old_visibility != visibility:
                profile.profile_visibility = visibility
                profile.save(update_fields=["profile_visibility", "updated_at"])
                changed.append(("profile_visibility", old_visibility, visibility))

        settings_dirty = False
        for field in PRIVACY_FIELDS:
            if field not in data:
                continue
            old_val = getattr(settings, field)
            new_val = bool(data[field])
            if old_val != new_val:
                setattr(settings, field, new_val)
                settings_dirty = True
                changed.append((field, old_val, new_val))

        if settings_dirty:
            settings.save()

        if not changed:
            return {
                "data": self.account.build_privacy_settings(profile, settings),
                "message": "Privacy settings updated successfully.",
                "changed_fields": [],
            }

        ip_address = request_meta.get("ip_address")
        user_agent = request_meta.get("user_agent", "")
        for field, old_val, new_val in changed:
            self.audit.record(
                domain=DomainType.IT,
                user_id=profile.user_id,
                event_type=f"privacy.{field}.changed",
                title=f"{PRIVACY_FIELD_LABELS[field]} updated",
                description=f"Changed from {old_val} to {new_val}.",
                ip_address=ip_address,
                metadata={
                    "field": field,
                    "previous_value": old_val,
                    "new_value": new_val,
                    "user_agent": user_agent,
                },
            )

        changed_fields = [field for field, _, _ in changed]
        self.sync.on_privacy_changed(profile, changed_fields)

        if len(changed) == 1:
            message = PRIVACY_SUCCESS_MESSAGES.get(
                changed[0][0], "Privacy settings updated successfully."
            )
        else:
            message = "Privacy settings updated successfully."

        return {
            "data": self._build_privacy_payload(profile, settings),
            "message": message,
            "changed_fields": changed_fields,
        }

    def _build_privacy_payload(self, profile: JobSeekerProfile, settings) -> dict:
        payload = self.account.build_privacy_settings(profile, settings)
        payload["visibility_options"] = self.privacy.visibility_options_for_ui()
        return payload
