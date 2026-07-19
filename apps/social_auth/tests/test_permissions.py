"""Tests for permission classes."""

from __future__ import annotations

from unittest.mock import MagicMock

from apps.social_auth.permissions import (
    IsAuthenticatedAndActive,
    SocialAuthIsAuthenticated,
)
from rest_framework.permissions import IsAuthenticated


class TestIsAuthenticatedAndActive:
    def test_authenticated_active_user_has_permission(self):
        permission = IsAuthenticatedAndActive()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_deleted = False
        assert permission.has_permission(request, None) is True

    def test_authenticated_deleted_user_denied(self):
        permission = IsAuthenticatedAndActive()
        request = MagicMock()
        request.user.is_authenticated = True
        request.user.is_deleted = True
        assert permission.has_permission(request, None) is False

    def test_unauthenticated_user_denied(self):
        permission = IsAuthenticatedAndActive()
        request = MagicMock()
        request.user.is_authenticated = False
        request.user.is_deleted = False
        assert permission.has_permission(request, None) is False

    def test_anonymous_user_denied(self):
        permission = IsAuthenticatedAndActive()
        request = MagicMock()
        request.user.is_authenticated = False
        request.user.is_deleted = False
        assert permission.has_permission(request, None) is False


class TestSocialAuthIsAuthenticated:
    def test_is_re_exported_standard_permission(self):
        """SocialAuthIsAuthenticated should be the standard DRF IsAuthenticated."""
        assert SocialAuthIsAuthenticated is IsAuthenticated
