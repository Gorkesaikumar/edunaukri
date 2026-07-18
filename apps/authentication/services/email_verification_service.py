from django.utils import timezone

from apps.accounts.constants.enums import AccountStatus
from apps.accounts.repositories.user_repository import DOMAIN_USER_MODELS
from apps.authentication.models import AuthToken, AuthTokenPurpose
from apps.authentication.repositories.auth_token_repository import AuthTokenRepository
from apps.authentication.services.auth_email_service import AuthEmailService
from apps.core.exceptions.domain_exceptions import ValidationException
from apps.core.services.base import BaseService


class EmailVerificationService(BaseService):
    TOKEN_TTL_HOURS = 72

    def __init__(self):
        self.token_repository = AuthTokenRepository()

    @BaseService.atomic
    def create_verification_token(self, *, domain: str, user_id) -> str:
        model = DOMAIN_USER_MODELS.get(domain)
        if not model:
            raise ValidationException("Invalid domain.")

        user = model.objects.get(pk=user_id, is_deleted=False)
        raw, token_hash = AuthToken.generate()
        self.token_repository.create(
            domain=domain,
            user_id=user.pk,
            email=user.email,
            purpose=AuthTokenPurpose.EMAIL_VERIFICATION,
            token_hash=token_hash,
            expires_at=AuthToken.default_expiry(self.TOKEN_TTL_HOURS),
        )
        AuthEmailService().queue_verification_email(
            domain=domain,
            user_id=user.pk,
            email=user.email,
            raw_token=raw,
        )
        return raw

    @BaseService.atomic
    def request_resend(
        self, *, domain: str, email: str | None = None, user=None
    ) -> str | None:
        model = DOMAIN_USER_MODELS.get(domain)
        if not model:
            raise ValidationException("Invalid domain.")

        if user is not None:
            target = user
        elif email:
            target = model.objects.filter(
                email=email.lower().strip(), is_deleted=False
            ).first()
            if target is None:
                return None
        else:
            raise ValidationException("Email or authenticated user is required.")

        if target.email_verified:
            raise ValidationException("Email is already verified.")

        self.token_repository.invalidate_pending(
            domain=domain,
            user_id=target.pk,
            purpose=AuthTokenPurpose.EMAIL_VERIFICATION,
        )
        return self.create_verification_token(domain=domain, user_id=target.pk)

    @BaseService.atomic
    def verify(self, *, domain: str, token: str) -> bool:
        model = DOMAIN_USER_MODELS.get(domain)
        if not model:
            raise ValidationException("Invalid domain.")

        auth_token = self.token_repository.get_by_hash(
            domain=domain,
            token_hash=AuthToken.hash_token(token),
            purpose=AuthTokenPurpose.EMAIL_VERIFICATION,
        )

        if not auth_token or not auth_token.is_valid:
            raise ValidationException("Invalid or expired verification token.")

        user = model.objects.get(pk=auth_token.user_id)
        user.email_verified = True
        if user.account_status == AccountStatus.PENDING_VERIFICATION:
            user.account_status = AccountStatus.ACTIVE
        user.save(update_fields=["email_verified", "account_status", "updated_at"])

        self.token_repository.update(auth_token, used_at=timezone.now())
        return True
