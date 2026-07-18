from django.db import models


class AdminRoleType(models.TextChoices):
    SUPER_ADMIN = "super_admin", "Super Admin"
    ADMIN = "admin", "Admin"
    SUPPORT_ADMIN = "support_admin", "Support Admin"
    FINANCE_ADMIN = "finance_admin", "Finance Admin"
    MODERATOR = "moderator", "Moderator"


class PlatformSettingCategory(models.TextChoices):
    PLATFORM = "platform", "Platform"
    BILLING = "billing", "Billing"
    GUARANTEE = "guarantee", "Guarantee"
    LIMITS = "limits", "Limits"
    ROLES = "roles", "Roles"
