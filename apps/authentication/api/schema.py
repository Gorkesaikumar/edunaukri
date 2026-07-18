from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers

from apps.authentication.api.v1.serializers import (
    EmailVerifySerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SessionLoginSerializer,
    UserActivationSerializer,
)

MessageResponse = inline_serializer(
    name="AuthMessageResponse",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            name="AuthMessageData",
            fields={"message": serializers.CharField()},
        ),
    },
)

RegistrationResponse = inline_serializer(
    name="RegistrationResponse",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            name="RegistrationData",
            fields={
                "id": serializers.UUIDField(),
                "email": serializers.EmailField(),
                "domain": serializers.CharField(),
                "account_status": serializers.CharField(),
                "verification_token": serializers.CharField(required=False),
                "role": serializers.CharField(required=False),
                "roles": serializers.ListField(
                    child=serializers.CharField(), required=False
                ),
            },
        ),
    },
)

UserContextResponse = inline_serializer(
    name="UserContextResponse",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            name="UserContextData",
            fields={
                "id": serializers.UUIDField(),
                "email": serializers.EmailField(),
                "domain": serializers.CharField(),
                "account_status": serializers.CharField(),
                "roles": serializers.ListField(
                    child=serializers.CharField(), required=False
                ),
                "profile_initialized": serializers.BooleanField(),
                "profile_status": serializers.CharField(required=False),
                "profile_completeness": serializers.IntegerField(required=False),
                "college_id": serializers.UUIDField(required=False),
            },
        ),
    },
)

JWTTokenResponse = inline_serializer(
    name="JWTTokenResponse",
    fields={
        "success": serializers.BooleanField(),
        "data": inline_serializer(
            name="JWTTokenData",
            fields={
                "access": serializers.CharField(),
                "refresh": serializers.CharField(),
                "domain": serializers.CharField(),
                "roles": serializers.ListField(
                    child=serializers.CharField(), required=False
                ),
                "primary_role": serializers.CharField(required=False),
            },
        ),
    },
)

REGISTER_EXAMPLES = [
    OpenApiExample(
        "Job seeker registration",
        value={"email": "seeker@example.com", "password": "SecurePass123!@#"},
        request_only=True,
    ),
]

register_schema = extend_schema(
    tags=["auth-registration"],
    summary="Register a domain user",
    request=RegisterSerializer,
    responses={201: RegistrationResponse},
    examples=REGISTER_EXAMPLES,
)

password_reset_request_schema = extend_schema(
    tags=["auth-password"],
    summary="Request password reset",
    request=PasswordResetRequestSerializer,
    responses={200: MessageResponse},
)

password_reset_confirm_schema = extend_schema(
    tags=["auth-password"],
    summary="Confirm password reset",
    request=PasswordResetConfirmSerializer,
    responses={200: MessageResponse},
)

password_change_schema = extend_schema(
    tags=["auth-password"],
    summary="Change password (authenticated)",
    request=PasswordChangeSerializer,
    responses={200: MessageResponse},
)

email_verify_schema = extend_schema(
    tags=["auth-verification"],
    summary="Verify email address",
    request=EmailVerifySerializer,
    responses={200: MessageResponse},
)

logout_schema = extend_schema(
    tags=["auth-session"],
    summary="Logout (JWT refresh blacklist)",
    request=LogoutSerializer,
    responses={200: MessageResponse},
)

me_schema = extend_schema(
    tags=["auth-profile"],
    summary="Current user context",
    responses={200: UserContextResponse},
)

session_login_schema = extend_schema(
    tags=["auth-session"],
    summary="Session login for a domain",
    request=SessionLoginSerializer,
    responses={200: UserContextResponse},
)

session_logout_schema = extend_schema(
    tags=["auth-session"],
    summary="Session logout",
    responses={200: MessageResponse},
)

user_lifecycle_schema = extend_schema(
    tags=["auth-admin"],
    summary="Admin user lifecycle action",
    request=UserActivationSerializer,
    responses={200: MessageResponse},
)

jwt_obtain_schema = extend_schema(
    tags=["auth-jwt"],
    summary="Obtain domain JWT pair",
    responses={200: JWTTokenResponse},
)

jwt_refresh_schema = extend_schema(
    tags=["auth-jwt"],
    summary="Refresh JWT access token",
    responses={200: OpenApiResponse(description="New access token issued.")},
)
