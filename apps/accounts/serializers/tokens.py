from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.faculty_user import FacultyUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.services.login_service import LoginService
from apps.authentication.services.session_management_service import (
    SessionManagementService,
)
from apps.authentication.services.token_rotation_service import TokenRotationService
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)


class DomainTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Base serializer for domain-specific JWT token issuance."""

    username_field = "email"
    user_model = None
    domain = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "username" in self.fields:
            self.fields.pop("username")
        self.fields["email"] = serializers.EmailField(required=True)

    @classmethod
    def get_token(cls, user):
        token = RefreshToken()
        token["user_id"] = str(user.pk)
        token["user_uuid"] = str(user.pk)
        token["domain"] = cls.domain
        token["email"] = user.email
        if cls.domain == "it":
            roles = RoleAssignmentService().get_it_roles(user)
            token["roles"] = roles
            token["primary_role"] = roles[0] if roles else None
        return token

    def validate(self, attrs):
        import uuid

        request = self.context.get("request")
        meta = {}
        if request:
            meta = {
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
            }

        user = LoginService().authenticate(
            domain=self.domain,
            email=attrs.get("email"),
            password=attrs.get("password"),
            request_meta=meta,
        )

        session_uuid = uuid.uuid4()
        refresh = self.get_token(user)
        refresh["session_uuid"] = str(session_uuid)

        session = SessionManagementService().register_session(
            domain=self.domain,
            user_id=user.pk,
            refresh_token=str(refresh),
            request_meta=meta,
            session_uuid=session_uuid,
            auth_method="password",
        )

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "domain": self.domain,
            "user_uuid": str(user.pk),
            "session_uuid": str(session.session_uuid),
        }
        if self.domain == "it":
            data["roles"] = list(refresh.get("roles", []))
            data["primary_role"] = refresh.get("primary_role")
        return data


class DomainTokenRefreshSerializer(TokenRefreshSerializer):
    """Domain-aware refresh token rotation with session synchronization."""

    def validate(self, attrs):
        request = self.context.get("request")
        meta = {}
        if request:
            meta = {
                "ip_address": request.META.get("REMOTE_ADDR"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:500],
            }

        try:
            access, rotated = TokenRotationService().refresh_tokens(
                refresh_token=attrs["refresh"],
                request_meta=meta,
            )
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

        token = RefreshToken(rotated or attrs["refresh"])
        data = {
            "access": access,
            "user_uuid": token.get("user_uuid") or token.get("user_id"),
            "session_uuid": token.get("session_uuid"),
        }
        if rotated:
            data["refresh"] = rotated
        return data


class AdminTokenObtainPairSerializer(DomainTokenObtainPairSerializer):
    user_model = AdminUser
    domain = "admin"


class ITTokenObtainPairSerializer(DomainTokenObtainPairSerializer):
    user_model = ITUser
    domain = "it"


class FacultyTokenObtainPairSerializer(DomainTokenObtainPairSerializer):
    user_model = FacultyUser
    domain = "faculty"


class ProfessorTokenObtainPairSerializer(DomainTokenObtainPairSerializer):
    user_model = ProfessorUser
    domain = "professor"


class CollegeTokenObtainPairSerializer(DomainTokenObtainPairSerializer):
    user_model = CollegeUser
    domain = "college"
