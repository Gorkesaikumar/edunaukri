"""Domain signals for Social Auth — dispatched after successful social login.

Signal: ``social_login_completed``
---------------------------------
Sent after a user successfully authenticates via a social provider.

Provides::

    sender: GoogleLoginService (or provider-specific login service)
    user: ITUser — the authenticated local user
    social_account_id: str — UUID of the linked SocialAccount
    provider: str — provider name (e.g. ``"google"``, ``"linkedin"``)
    request_meta: dict | None — IP / user-agent metadata for audit

Handlers:
---------
+---------------------------+----------+----------------------------+
| Handler                   | Cost     | Why                        |
+---------------------------+----------+----------------------------+
| update_login_fields       | light    | Single-row ORM update      |
| sync_provider_profile     | light    | Single-row ORM update      |
| create_login_notification | heavy    | DB write + possible WS push|
+---------------------------+----------+----------------------------+

Heavy work (notification) is dispatched to Celery.
"""

from __future__ import annotations

import logging

from django.dispatch import Signal, receiver
from django.utils import timezone

from apps.social_auth.models import SocialAccount

logger = logging.getLogger(__name__)


# ==========================================================================
# Custom signal
# ==========================================================================

social_login_completed = Signal()


# ==========================================================================
# Lightweight handlers — run inline in the request thread
# ==========================================================================


@receiver(social_login_completed)
def update_login_fields(sender, **kwargs):
    """Update ``last_login_at`` on the ``SocialAccount`` in real time.

    This is a single-row ORM update — negligible cost.  It keeps the
    dashboard / profile page accurate immediately after login without
    waiting for a background worker.
    """
    social_account_id: str | None = kwargs.get("social_account_id")
    if not social_account_id:
        return

    try:
        SocialAccount.objects.filter(pk=social_account_id).update(
            last_login_at=timezone.now(),
        )
    except Exception:
        logger.exception(
            "Failed to update last_login for SocialAccount %s", social_account_id
        )


@receiver(social_login_completed)
def sync_provider_profile(sender, **kwargs):
    """Sync the provider's latest display_name and profile_picture.

    The ``GoogleOAuthService`` already passes these values in the
    ``GoogleTokenData`` which are stored on the ``SocialAccount`` at
    creation / link time.  This handler re-applies them on every login so
    that if a user updates their Google / LinkedIn profile, the changes
    propagate here on next sign-in.
    """
    social_account_id: str | None = kwargs.get("social_account_id")
    if not social_account_id:
        return

    # The caller (login service) already updated these fields via
    # ``SocialAccountService`` — this handler is a safety net for any
    # edge case where the service omitted them.
    # Currently a no-op; expand when provider-specific services push
    # updated profile data into the signal kwargs.
    _profile = kwargs.get("profile")
    if not _profile:
        return

    try:
        SocialAccount.objects.filter(pk=social_account_id).update(
            display_name=getattr(_profile, "name", ""),
            profile_picture=getattr(_profile, "picture", ""),
        )
    except Exception:
        logger.exception(
            "Failed to sync provider profile for SocialAccount %s",
            social_account_id,
        )


# ==========================================================================
# Heavy handler — dispatched to Celery
# ==========================================================================


@receiver(social_login_completed)
def queue_login_notification(sender, **kwargs):
    """Dispatch a Celery task to create an in-app login notification.

    The actual DB write and any WebSocket push happen in the background
    so the login response is not delayed.
    """
    try:
        from apps.social_auth.tasks import create_social_login_notification_task

        create_social_login_notification_task.delay(
            user_id=str(kwargs["user"].pk),
            provider=kwargs.get("provider", ""),
            social_account_id=kwargs.get("social_account_id", ""),
        )
    except Exception:
        logger.exception("Failed to queue social login notification task")
