from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class AuthEndpointThrottle(SimpleRateThrottle):
    """Legacy generic auth throttle — prefer specialized throttles below."""

    scope = "auth"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": f"{ident}:{request.path}",
        }


class RegistrationThrottle(SimpleRateThrottle):
    scope = "auth_registration"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LoginEndpointThrottle(SimpleRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        email = ""
        if hasattr(request, "data") and request.data:
            email = request.data.get("email", "")
        return self.cache_format % {"scope": self.scope, "ident": f"{ident}:{email}"}


class PasswordResetRequestThrottle(SimpleRateThrottle):
    scope = "auth_password_reset"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        email = ""
        if hasattr(request, "data") and request.data:
            email = request.data.get("email", "")
        return self.cache_format % {"scope": self.scope, "ident": f"{ident}:{email}"}


class PasswordChangeThrottle(UserRateThrottle):
    scope = "auth_password_change"


class EmailVerifyThrottle(SimpleRateThrottle):
    scope = "auth_email_verify"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class TokenRefreshThrottle(SimpleRateThrottle):
    scope = "auth_token_refresh"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class AdminAuthThrottle(UserRateThrottle):
    scope = "auth_admin"


class LoginIPThrottle(SimpleRateThrottle):
    """IP-based rate limit for login endpoints (protect against brute force)."""
    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class OTPThrottle(SimpleRateThrottle):
    """Rate limit for OTP / email verification attempts."""
    scope = "otp"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        token = ""
        if hasattr(request, "data") and request.data:
            token = request.data.get("token", "") or request.data.get("code", "")
        return self.cache_format % {"scope": self.scope, "ident": f"{ident}:{token}"}


class ApplicationThrottle(UserRateThrottle):
    """Rate limit for job application submissions and management."""
    scope = "applications"


class ResumeUploadThrottle(UserRateThrottle):
    """Rate limit for file and resume uploads."""
    scope = "resume_upload"


class InvoiceAPIThrottle(UserRateThrottle):
    """Rate limit for invoice generation and queries."""
    scope = "invoices"


class DashboardAPIThrottle(UserRateThrottle):
    """Rate limit for portal analytics and dashboard metrics."""
    scope = "dashboard"


class ReportsAPIThrottle(UserRateThrottle):
    """Rate limit for heavy report generation and data exports."""
    scope = "reports"


class NotificationsAPIThrottle(UserRateThrottle):
    """Rate limit for notification queries and status updates."""
    scope = "notifications"


class BruteForceIPThrottle(SimpleRateThrottle):
    """Global IP rate limit across high-risk endpoints to prevent brute-force attacks."""
    scope = "brute_force_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }
