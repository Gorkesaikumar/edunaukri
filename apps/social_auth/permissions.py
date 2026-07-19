"""
Social Auth — permissions
DRF and Django permission classes for this app.
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission, IsAuthenticated


class IsAuthenticatedAndActive(BasePermission):
    """Allow access only to authenticated, non-deleted users."""

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and not getattr(request.user, "is_deleted", False)
        )


# Re-export standard permission for convenience.
SocialAuthIsAuthenticated = IsAuthenticated
