"""Permanent public identity helpers — UUID is the user's primary key."""

from __future__ import annotations

import uuid


class IdentityService:
    """Resolve and compare permanent user UUIDs (UUID v4 primary keys)."""

    @staticmethod
    def public_uuid(user) -> str:
        """Return the permanent public UUID for a domain user."""
        return str(user.pk)

    @staticmethod
    def normalize_uuid(value) -> str | None:
        """Normalize any UUID-like value; return None when invalid."""
        if value is None:
            return None
        try:
            return str(uuid.UUID(str(value)))
        except (ValueError, AttributeError, TypeError):
            return None

    @staticmethod
    def uuids_match(authenticated_uuid, url_uuid) -> bool:
        left = IdentityService.normalize_uuid(authenticated_uuid)
        right = IdentityService.normalize_uuid(url_uuid)
        return bool(left and right and left == right)
