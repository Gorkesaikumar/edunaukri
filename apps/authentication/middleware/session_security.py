from django.contrib.auth import logout as django_logout

from apps.authentication.validators.account_validator import (
    get_account_access_block_reason,
)


class SessionSecurityMiddleware:
    """Invalidate sessions for locked, suspended, or unverified accounts."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            reason = get_account_access_block_reason(user)
            if reason:
                django_logout(request)
                if hasattr(request, "session"):
                    request.session.flush()
        return self.get_response(request)
