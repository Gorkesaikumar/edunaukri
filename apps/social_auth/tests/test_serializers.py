"""Tests for serializers — GoogleLoginSerializer and GoogleCallbackSerializer."""

from __future__ import annotations

from apps.social_auth.serializers import (
    GoogleCallbackSerializer,
    GoogleLoginSerializer,
    SocialAccountSerializer,
)


class TestSocialAccountSerializer:
    def test_read_only_fields(self):
        serializer = SocialAccountSerializer()
        assert "created_at" in serializer.Meta.read_only_fields
        assert "updated_at" in serializer.Meta.read_only_fields
        assert "id" in serializer.Meta.read_only_fields

    def test_valid_data(self, it_user):
        data = {
            "user": it_user.pk,
            "provider": "google",
            "email": "test@example.com",
        }
        serializer = SocialAccountSerializer(data=data)
        assert serializer.is_valid() is True


class TestGoogleLoginSerializer:
    def test_empty_body_is_valid(self):
        """Login serializer no longer requires redirect_uri."""
        serializer = GoogleLoginSerializer(data={})
        assert serializer.is_valid() is True

    def test_extra_fields_rejected(self):
        """Extra fields (like redirect_uri) are rejected by DRF."""
        serializer = GoogleLoginSerializer(
            data={"redirect_uri": "https://example.com/callback"}
        )
        assert serializer.is_valid() is False


class TestGoogleCallbackSerializer:
    def test_valid_data(self):
        """Callback only requires the authorization code."""
        serializer = GoogleCallbackSerializer(
            data={"code": "4/0AX4Xf..."}
        )
        assert serializer.is_valid() is True

    def test_missing_code(self):
        serializer = GoogleCallbackSerializer(data={})
        assert serializer.is_valid() is False
        assert "code" in serializer.errors

    def test_extra_fields_rejected(self):
        """redirect_uri is no longer accepted in the request body."""
        serializer = GoogleCallbackSerializer(
            data={"code": "some_code", "redirect_uri": "https://example.com/callback"}
        )
        assert serializer.is_valid() is False
