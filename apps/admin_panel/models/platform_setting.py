from django.db import models

from apps.admin_panel.constants.enums import PlatformSettingCategory
from apps.core.models.base import AuditedBaseModel


class PlatformSetting(AuditedBaseModel):
    key = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.CharField(
        max_length=30,
        choices=PlatformSettingCategory.choices,
        default=PlatformSettingCategory.PLATFORM,
        db_index=True,
    )
    value = models.JSONField(default=dict)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "admin_platform_setting"
        ordering = ["category", "key"]

    def __str__(self):
        return self.key
