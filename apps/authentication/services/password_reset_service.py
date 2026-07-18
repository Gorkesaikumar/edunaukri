from apps.authentication.validators.password_validator import validate_password_strength
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.authentication.models import AuthToken, AuthTokenPurpose
from apps.accounts.repositories.user_repository import DOMAIN_USER_MODELS
from apps.authentication.repositories.auth_token_repository import AuthTokenRepository
from apps.authentication.services.auth_email_service import AuthEmailService
from apps.core.services.base import BaseService


class PasswordResetService(BaseService):
    TOKEN_TTL_HOURS = 24

    def __init__(self):
        self.token_repository = AuthTokenRepository()

    @BaseService.atomic
    def request_reset(self, *, domain: str, email: str) -> str | None:
        """Create reset token. Returns raw token when email delivery is disabled (dev)."""
        model = DOMAIN_USER_MODELS.get(domain)
        if not model:
            raise ValidationError("Invalid domain.")

        email = email.lower().strip()
        try:
            user = model.objects.get(email=email, is_deleted=False, is_active=True)
        except model.DoesNotExist:
            return None

        self.token_repository.invalidate_pending(
            domain=domain,
            user_id=user.pk,
            purpose=AuthTokenPurpose.PASSWORD_RESET,
        )

        raw, token_hash = AuthToken.generate()
        self.token_repository.create(
            domain=domain,
            user_id=user.pk,
            email=email,
            purpose=AuthTokenPurpose.PASSWORD_RESET,
            token_hash=token_hash,
            expires_at=AuthToken.default_expiry(self.TOKEN_TTL_HOURS),
        )
        AuthEmailService().queue_password_reset_email(
            domain=domain,
            user_id=user.pk,
            email=email,
            raw_token=raw,
        )
        return raw

    @BaseService.atomic
    def confirm_reset(self, *, domain: str, token: str, new_password: str) -> bool:
        model = DOMAIN_USER_MODELS.get(domain)
        if not model:
            raise ValidationError("Invalid domain.")

        validate_password_strength(new_password)
        auth_token = self.token_repository.get_by_hash(
            domain=domain,
            token_hash=AuthToken.hash_token(token),
            purpose=AuthTokenPurpose.PASSWORD_RESET,
        )

        if not auth_token or not auth_token.is_valid:
            raise ValidationError("Invalid or expired reset token.")

        user = model.objects.get(pk=auth_token.user_id)
        user.set_password(new_password)
        user.save(update_fields=["password"])

        self.token_repository.update(auth_token, used_at=timezone.now())
        return True
