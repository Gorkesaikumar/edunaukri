from django.core.exceptions import ValidationError

from django.db import transaction


from apps.accounts.repositories.user_repository import get_user_repository

from apps.authentication.models import LoginAttemptResult

from apps.authentication.repositories.login_attempt_repository import (
    LoginAttemptRepository,
)

from apps.authentication.services.auth_audit_service import AuthAuditService

from apps.authentication.services.session_management_service import (
    SessionManagementService,
)

from apps.core.services.base import BaseService

from rest_framework_simplejwt.tokens import RefreshToken


class LoginService(BaseService):
    """Centralized credential verification with lockout and audit hooks."""

    def __init__(self):

        self.login_attempt_repository = LoginAttemptRepository()

        self.auth_audit = AuthAuditService()

    def authenticate(
        self,
        *,
        domain: str,
        email: str,
        password: str,
        request_meta: dict | None = None,
    ):

        repo = get_user_repository(domain)

        user = repo.get_by_email(email)

        if user is None and domain == "it":
            user = self._get_it_user_by_mobile(repo, email)

        meta = request_meta or {}

        if user is None:
            self._record_attempt(
                domain,
                email,
                None,
                LoginAttemptResult.FAILURE,
                meta,
                "invalid_credentials",
            )

            raise ValidationError("Invalid credentials.")

        if user.is_locked:
            self._record_attempt(
                domain,
                email,
                user.pk,
                LoginAttemptResult.LOCKED,
                meta,
                "account_locked",
            )

            raise ValidationError("Account is temporarily locked. Try again later.")

        if not user.is_active or user.is_deleted:
            self._record_attempt(
                domain,
                email,
                user.pk,
                LoginAttemptResult.FAILURE,
                meta,
                "inactive_account",
            )

            raise ValidationError("Invalid credentials.")

        from apps.accounts.constants.enums import AccountStatus

        if user.account_status in (AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED):
            self._record_attempt(
                domain,
                email,
                user.pk,
                LoginAttemptResult.FAILURE,
                meta,
                "account_suspended",
            )

            raise ValidationError("Account is not active.")

        from django.conf import settings

        if (
            getattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", False)
            and hasattr(user, "email_verified")
            and not user.email_verified
        ):
            self._record_attempt(
                domain,
                email,
                user.pk,
                LoginAttemptResult.FAILURE,
                meta,
                "email_unverified",
            )

            raise ValidationError("Email verification required.")

        if not user.check_password(password):
            user.record_failed_login(
                lock_after=getattr(settings, "AUTH_MAX_FAILED_LOGIN_ATTEMPTS", 5),
                lock_minutes=getattr(settings, "AUTH_LOCKOUT_MINUTES", 30),
            )

            self._record_attempt(
                domain,
                email,
                user.pk,
                LoginAttemptResult.FAILURE,
                meta,
                "invalid_credentials",
            )

            raise ValidationError("Invalid credentials.")

        user.reset_login_attempts()

        self._record_attempt(
            domain, email, user.pk, LoginAttemptResult.SUCCESS, meta, ""
        )

        return user

    @staticmethod
    def _get_it_user_by_mobile(repo, identifier: str):
        """Allow recruiters registered with mobile-only to sign in using their phone number."""

        from apps.it_recruitment.services.web_registration_service import (
            IT_MOBILE_EMAIL_DOMAIN,
            normalize_mobile,
        )

        digits = normalize_mobile(identifier)

        if not digits:
            return None

        provisional = f"{digits}@{IT_MOBILE_EMAIL_DOMAIN}"

        user = repo.get_by_email(provisional)

        if user:
            return user

        from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile

        seeker = (
            JobSeekerProfile.objects.filter(phone=digits, is_deleted=False)
            .select_related("user")
            .first()
        )

        if seeker and not seeker.user.is_deleted:
            return seeker.user

        recruiter = (
            RecruiterProfile.objects.filter(phone=digits, is_deleted=False)
            .select_related("user")
            .first()
        )

        if recruiter and not recruiter.user.is_deleted:
            return recruiter.user

        return None

    def _record_attempt(self, domain, email, user_id, result, meta, reason):

        self.login_attempt_repository.create(
            domain=domain,
            email=email.lower().strip(),
            user_id=user_id,
            result=result,
            ip_address=meta.get("ip_address"),
            user_agent=meta.get("user_agent", "")[:500],
            failure_reason=reason,
        )

        if (
            result in (LoginAttemptResult.FAILURE, LoginAttemptResult.LOCKED)
            and user_id
        ):
            self.auth_audit.record_login_failure(
                domain=domain,
                email=email,
                user_id=user_id,
                reason=reason,
                request_meta=meta,
            )


class LogoutService(BaseService):
    def __init__(self):

        self.sessions = SessionManagementService()

        self.auth_audit = AuthAuditService()

    @transaction.atomic
    def logout(self, *, refresh_token: str, request_meta: dict | None = None) -> None:

        meta = request_meta or {}

        domain = None

        user_id = None

        session_uuid = None

        try:
            token = RefreshToken(refresh_token)

            domain = token.get("domain")

            user_id = token.get("user_id")

            session_uuid = token.get("session_uuid")

            token.blacklist()

        except Exception as exc:
            raise ValidationError("Invalid refresh token.") from exc

        self.sessions.revoke_by_refresh_token(refresh_token, request_meta=meta)

        if domain and user_id:
            self.auth_audit.record_logout(
                domain=domain,
                user_id=user_id,
                session_uuid=str(session_uuid) if session_uuid else None,
                request_meta=meta,
            )
