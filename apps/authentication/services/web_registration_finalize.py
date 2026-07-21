"""Shared post-registration flow for domain web signup."""

from __future__ import annotations

import logging
from typing import Callable

from django.conf import settings

from apps.accounts.constants.enums import AccountStatus
from apps.authentication.services.session_service import SessionService
from apps.core.services.base import BaseService

logger = logging.getLogger(__name__)


class WebRegistrationFinalizeService(BaseService):
    """Session bootstrap, verification email, and dashboard redirect after web signup."""

    def finalize(
        self,
        request,
        *,
        user,
        domain: str,
        password: str,
        dashboard_url_resolver: Callable,
    ) -> dict:
        redirect_url = None
        requires_verification = False

        if user.account_status != AccountStatus.SUSPENDED:
            SessionService().login(
                request,
                domain=domain,
                email=user.email,
                password=password,
            )
            redirect_url = dashboard_url_resolver(user)

        return {
            "user_id": str(user.pk),
            "user": user,
            "requires_verification": requires_verification,
            "redirect_url": redirect_url,
        }
