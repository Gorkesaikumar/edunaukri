"""
Social Auth — serializers
DRF serializers for request/response mapping. No business logic.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.social_auth.models import SocialAccount


class SocialAccountSerializer(serializers.ModelSerializer):
    """Read/write serializer for SocialAccount.

    .. note::

        The ``user`` field is a ``GenericForeignKey``, so DRF cannot
        auto-discover it.  We expose the resolved user as a read-only
        JSON object via ``user_info`` instead.
    """

    user_info = serializers.SerializerMethodField(
        help_text="Resolved user object (id, email, domain).",
    )

    class Meta:
        model = SocialAccount
        fields = (
            "id",
            "user_info",
            "provider",
            "email",
            "display_name",
            "is_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_user_info(self, obj: SocialAccount) -> dict | None:
        """Return the resolved user as a lightweight JSON object."""
        user = obj.user
        if user is None:
            return None
        return {
            "id": str(user.pk),
            "email": user.email,
            "domain": obj.user_domain,
        }


# ---------------------------------------------------------------------------
# Google OAuth — request serializers
# ---------------------------------------------------------------------------


class GoogleLoginSerializer(serializers.Serializer):
    """Initiates a Google OAuth login — returns the provider's authorization URL.

    The ``domain`` and ``role`` fields preserve the login context.  These
    are signed into the OAuth ``state`` parameter and validated on callback.

    Domain / role combinations:
    - ``it`` / ``seeker``    → IT job seeker
    - ``it`` / ``recruiter`` → IT recruiter
    - ``professor`` / ``seeker`` → faculty job seeker
    - ``college`` / ``institution`` → college / institution user
    """

    domain = serializers.ChoiceField(
        choices=["it", "professor", "college", "admin"],
        required=False,
        default="it",
        help_text="User domain (it, professor, college, admin). Default: it.",
    )
    role = serializers.ChoiceField(
        choices=["seeker", "recruiter", "institution", "admin"],
        required=False,
        default="seeker",
        help_text="User role within the domain. Default: seeker.",
    )
    login_url = serializers.CharField(
        required=False,
        default="",
        help_text="The login page URL the user is currently on (e.g. /it/login/job-seeker/). "
        "Stored in the signed OAuth state and used to redirect back on error.",
    )


class GoogleCallbackSerializer(serializers.Serializer):
    """Exchanges a Google authorization code for a verified profile + session.

    The ``state`` parameter is the signed token returned by
    ``GoogleLoginView``.  It contains the login context (domain, role)
    and is verified for authenticity and expiry server-side.
    """

    code = serializers.CharField(
        help_text="Authorization code received from Google's redirect.",
    )
    state = serializers.CharField(
        required=False,
        default="",
        help_text="Signed OAuth state token containing login context (domain, role, login_url).",
    )
