from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.authentication.services.session_revocation_service import (
    SessionRevocationService,
)
from apps.authentication.validators.account_validator import (
    get_account_access_block_reason,
)
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.faculty_user import FacultyUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser

DOMAIN_USER_MODELS = {
    "admin": AdminUser,
    "it": ITUser,
    "professor": ProfessorUser,
    "college": CollegeUser,
    "faculty": FacultyUser,
}


class DomainJWTAuthentication(JWTAuthentication):
    """Validate JWT tokens and resolve users from the correct domain model."""

    def get_user(self, validated_token):
        domain = validated_token.get("domain")
        user_id = validated_token.get("user_id")

        if not domain or not user_id:
            raise InvalidToken("Token missing domain or user_id claim.")

        model = DOMAIN_USER_MODELS.get(domain)
        if model is None:
            raise InvalidToken("Token contains an invalid domain claim.")

        try:
            user = model.objects.get(pk=user_id)
        except model.DoesNotExist as exc:
            raise InvalidToken("User not found.") from exc

        if not user.is_active or user.is_deleted:
            raise InvalidToken("User is inactive.")

        block_reason = get_account_access_block_reason(user)
        if block_reason:
            raise InvalidToken("User account is not permitted to authenticate.")

        revoked_at = SessionRevocationService().get_revoked_at(
            domain=domain, user_id=user_id
        )
        token_iat = validated_token.get("iat")
        if revoked_at and token_iat and token_iat < revoked_at.timestamp():
            raise InvalidToken("Session has been revoked.")

        return user
