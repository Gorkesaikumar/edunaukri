from rest_framework import permissions

from apps.core.permissions.base import IsPlatformAdmin


class IsEnterpriseAdmin(IsPlatformAdmin):
    """Enterprise admin panel access — active platform administrators only."""

    message = "Enterprise admin access required."
