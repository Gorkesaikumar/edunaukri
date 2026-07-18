from apps.admin_panel.constants.enums import PlatformSettingCategory
from apps.admin_panel.repositories.platform_setting_repository import (
    PlatformSettingRepository,
)
from apps.admin_panel.services.admin_audit import record_admin_action
from apps.core.services.base import BaseService
from apps.guarantee_claims.constants.enums import DEFAULT_GUARANTEE_DAYS


DEFAULT_SETTINGS = {
    "platform.name": {
        "category": PlatformSettingCategory.PLATFORM,
        "value": {"name": "Edunaukri"},
        "description": "Platform display name",
    },
    "platform.maintenance_mode": {
        "category": PlatformSettingCategory.PLATFORM,
        "value": {"enabled": False},
        "description": "Emergency Maintenance Lockdown Mode",
    },
    "billing.guarantee_days": {
        "category": PlatformSettingCategory.GUARANTEE,
        "value": {"days": DEFAULT_GUARANTEE_DAYS},
        "description": "Default placement guarantee period in days",
    },
    "limits.max_upload_mb": {
        "category": PlatformSettingCategory.LIMITS,
        "value": {"mb": 10},
        "description": "Maximum file upload size in megabytes",
    },
    "limits.max_applications_per_job": {
        "category": PlatformSettingCategory.LIMITS,
        "value": {"count": 500},
        "description": "Maximum applications per job posting",
    },
}


class AdminConfigService(BaseService):
    def __init__(self):
        self.repository = PlatformSettingRepository()

    def list_settings(self, *, category: str | None = None):
        self.ensure_defaults()
        qs = self.repository.filter_by(is_active=True)
        if category:
            qs = qs.filter(category=category)
        return qs.order_by("category", "key")

    def get_setting(self, key: str):
        self.ensure_defaults()
        return self.repository.filter_by(key=key).first()

    def update_setting(self, key: str, *, value: dict, admin_id, description: str = ""):
        from django.core.cache import cache

        setting = self.get_setting(key)
        if not setting:
            raise ValueError(f"Unknown setting: {key}")
        setting = self.repository.update(
            setting, value=value, description=description or setting.description
        )
        cache.delete(f"platform_setting:{key}")
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.setting.updated",
            entity_type="platform_setting",
            entity_id=setting.pk,
            payload={"key": key, "value": value},
        )
        return setting

    def ensure_defaults(self) -> None:
        for key, meta in DEFAULT_SETTINGS.items():
            if not self.repository.filter_by(key=key).exists():
                self.repository.create(
                    key=key,
                    category=meta["category"],
                    value=meta["value"],
                    description=meta["description"],
                )

    def as_dict(self) -> dict:
        return {s.key: s.value for s in self.list_settings()}
