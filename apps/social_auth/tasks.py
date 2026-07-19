"""Celery tasks for Social Auth — heavy post-login work dispatched from signals."""

from __future__ import annotations

import logging

from celery import shared_task

from apps.core.tasks import BaseTask

logger = logging.getLogger(__name__)


@shared_task(
    base=BaseTask,
    name="social_auth.create_login_notification",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=60,
    time_limit=90,
)
def create_social_login_notification_task(
    self,
    user_id: str,
    provider: str,
    social_account_id: str,
) -> dict:
    """Create an in-app notification confirming a successful social login.

    Runs in a background worker so the login response is not delayed.
    """
    from django.utils import timezone

    from apps.notifications.models import Notification
    from apps.notifications.constants.enums import NotificationChannel, NotificationStatus

    provider_display = provider.title() if provider else "Social"

    notification = Notification.objects.create(
        recipient_domain="it",
        recipient_id=user_id,
        channel=NotificationChannel.IN_APP,
        title=f"Signed in with {provider_display}",
        body=(
            f"You successfully signed in using your {provider_display} account. "
            f"If this wasn't you, please secure your account immediately."
        ),
        event_type="auth.social.login",
        entity_type="social_account",
        entity_id=social_account_id,
        status=NotificationStatus.DELIVERED,
        payload={
            "provider": provider,
            "social_account_id": social_account_id,
            "login_at": timezone.now().isoformat(),
        },
    )

    logger.info(
        "Login notification created for user=%s provider=%s notif=%s",
        user_id,
        provider,
        notification.pk,
    )

    return {
        "user_id": user_id,
        "provider": provider,
        "notification_id": str(notification.pk),
    }
