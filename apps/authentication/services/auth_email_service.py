from django.conf import settings

from apps.authentication.constants.events import (
    AUTH_EMAIL_VERIFICATION,
    AUTH_PASSWORD_RESET,
)
from apps.core.constants.enums import DomainType
from apps.core.services.base import BaseService
from apps.core.services.outbox_service import OutboxService


class AuthEmailService(BaseService):
    """Queue transactional auth emails through the outbox."""

    def expose_token_in_api(self) -> bool:
        return not getattr(settings, "AUTH_EMAIL_DELIVERY_ENABLED", False)

    def queue_verification_email(
        self, *, domain: str, user_id, email: str, raw_token: str
    ) -> None:
        if not getattr(settings, "AUTH_EMAIL_DELIVERY_ENABLED", False):
            return
        OutboxService().publish(
            domain=DomainType.PLATFORM,
            event_type=AUTH_EMAIL_VERIFICATION,
            aggregate_type="auth_token",
            aggregate_id=user_id,
            payload={
                "recipient_domain": domain,
                "recipient_id": str(user_id),
                "email": email,
                "token": raw_token,
                "send_email": True,
            },
        )

    def queue_password_reset_email(
        self, *, domain: str, user_id, email: str, raw_token: str
    ) -> None:
        if not getattr(settings, "AUTH_EMAIL_DELIVERY_ENABLED", False):
            return
        OutboxService().publish(
            domain=DomainType.PLATFORM,
            event_type=AUTH_PASSWORD_RESET,
            aggregate_type="auth_token",
            aggregate_id=user_id,
            payload={
                "recipient_domain": domain,
                "recipient_id": str(user_id),
                "email": email,
                "token": raw_token,
                "send_email": True,
            },
        )

    def _web_base_url(self) -> str:
        return getattr(settings, "WEB_BASE_URL", "").rstrip("/")

    def build_verification_url(self, *, domain: str, token: str) -> str:
        from django.urls import reverse
        from urllib.parse import urlencode

        web_base = self._web_base_url()
        if web_base:
            path = reverse("web_verify_email")
            query = urlencode({"domain": domain, "token": token})
            return f"{web_base}{path}?{query}"
        base = getattr(settings, "AUTH_FRONTEND_BASE_URL", "").rstrip("/")
        return f"{base}/verify-email?domain={domain}&token={token}"

    def build_password_reset_url(self, *, domain: str, token: str) -> str:
        from django.urls import reverse
        from urllib.parse import urlencode

        web_base = self._web_base_url()
        if web_base:
            path = reverse("web_reset_password")
            query = urlencode({"domain": domain, "token": token})
            return f"{web_base}{path}?{query}"
        base = getattr(settings, "AUTH_FRONTEND_BASE_URL", "").rstrip("/")
        return f"{base}/reset-password?domain={domain}&token={token}"
