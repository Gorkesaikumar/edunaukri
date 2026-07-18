import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.authentication.constants.events import (
    AUTH_EMAIL_VERIFICATION,
    AUTH_PASSWORD_RESET,
)
from apps.authentication.services.auth_email_service import AuthEmailService
from apps.core.models.outbox_event import OutboxEvent
from apps.core.services.base import BaseService

logger = logging.getLogger(__name__)


class AuthEmailDeliveryService(BaseService):
    """Deliver queued auth emails from outbox events."""

    def deliver(self, event: OutboxEvent) -> bool:
        payload = event.payload or {}
        email = payload.get("email")
        token = payload.get("token")
        domain = payload.get("recipient_domain")
        if not email or not token or not domain:
            logger.warning(
                "Auth email event %s missing required payload fields", event.pk
            )
            return False

        mailer = AuthEmailService()
        if event.event_type == AUTH_EMAIL_VERIFICATION:
            subject = "Verify your Edunaukri account"
            link = mailer.build_verification_url(domain=domain, token=token)
            body = (
                "Please verify your email address to activate your account.\n\n"
                f"Verification link: {link}\n\n"
                "If you did not create an account, you can ignore this message."
            )
        elif event.event_type == AUTH_PASSWORD_RESET:
            subject = "Reset your Edunaukri password"
            link = mailer.build_password_reset_url(domain=domain, token=token)
            body = (
                "We received a request to reset your password.\n\n"
                f"Reset link: {link}\n\n"
                "If you did not request a reset, you can ignore this message."
            )
        else:
            return False

        from_email = getattr(settings, "AUTH_EMAIL_FROM", None) or getattr(
            settings, "DEFAULT_FROM_EMAIL", None
        )
        if not from_email:
            logger.error(
                "Auth email delivery skipped: no AUTH_EMAIL_FROM or DEFAULT_FROM_EMAIL configured"
            )
            return False

        send_mail(subject, body, from_email, [email], fail_silently=False)
        logger.info("Auth email delivered for event %s to %s", event.event_type, email)
        return True
