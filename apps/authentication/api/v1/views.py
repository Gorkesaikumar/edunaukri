from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status

from apps.authentication.api.schema import (
    email_verify_schema,
    logout_schema,
    me_schema,
    password_change_schema,
    password_reset_confirm_schema,
    password_reset_request_schema,
    register_schema,
    session_login_schema,
    session_logout_schema,
    user_lifecycle_schema,
)
from apps.authentication.api.v1.serializers import (
    EmailVerifySerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendEmailVerifySerializer,
    SessionLoginSerializer,
    UserActivationSerializer,
)
from apps.authentication.permissions.throttles import (
    AdminAuthThrottle,
    BruteForceIPThrottle,
    EmailVerifyThrottle,
    LoginEndpointThrottle,
    LoginIPThrottle,
    OTPThrottle,
    PasswordChangeThrottle,
    PasswordResetRequestThrottle,
    RegistrationThrottle,
)
from apps.authentication.selectors.user_context_selector import UserContextSelector
from apps.authentication.services.auth_email_service import AuthEmailService
from apps.authentication.services.email_verification_service import (
    EmailVerificationService,
)
from apps.authentication.services.login_service import LogoutService
from apps.authentication.services.password_change_service import PasswordChangeService
from apps.authentication.services.password_reset_service import PasswordResetService
from apps.authentication.services.registration_service import RegistrationService
from apps.authentication.services.session_service import SessionService
from apps.authentication.services.user_activation_service import UserActivationService
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView


def _registration_payload(
    user, *, domain: str, verification_token: str, extra: dict | None = None
):
    data = {
        "id": str(user.pk),
        "email": user.email,
        "domain": domain,
        "account_status": user.account_status,
    }
    if AuthEmailService().expose_token_in_api():
        data["verification_token"] = verification_token
    if extra:
        data.update(extra)
    return data


@register_schema
class RegisterJobSeekerView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, RegistrationThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService().register_job_seeker(**serializer.validated_data)
        token = EmailVerificationService().create_verification_token(
            domain="it", user_id=user.pk
        )
        return self.success_response(
            _registration_payload(
                user,
                domain="it",
                verification_token=token,
                extra={"role": "job_seeker", "roles": ["job_seeker"]},
            ),
            status=status.HTTP_201_CREATED,
        )


@register_schema
class RegisterRecruiterView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, RegistrationThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService().register_recruiter(**serializer.validated_data)
        token = EmailVerificationService().create_verification_token(
            domain="it", user_id=user.pk
        )
        return self.success_response(
            _registration_payload(
                user,
                domain="it",
                verification_token=token,
                extra={"role": "recruiter", "roles": ["recruiter"]},
            ),
            status=status.HTTP_201_CREATED,
        )


@register_schema
class RegisterITUserView(EnvelopeAPIView):
    """Legacy generic IT registration."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, RegistrationThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService().register_it_user(**serializer.validated_data)
        token = EmailVerificationService().create_verification_token(
            domain="it", user_id=user.pk
        )
        return self.success_response(
            _registration_payload(user, domain="it", verification_token=token),
            status=status.HTTP_201_CREATED,
        )


@register_schema
class RegisterProfessorView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, RegistrationThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService().register_professor(**serializer.validated_data)
        token = EmailVerificationService().create_verification_token(
            domain="professor", user_id=user.pk
        )
        return self.success_response(
            _registration_payload(
                user,
                domain="professor",
                verification_token=token,
                extra={"role": "professor"},
            ),
            status=status.HTTP_201_CREATED,
        )


@register_schema
class RegisterCollegeUserView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, RegistrationThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = RegistrationService().register_college_user(**serializer.validated_data)
        token = EmailVerificationService().create_verification_token(
            domain="college", user_id=user.pk
        )
        return self.success_response(
            _registration_payload(
                user,
                domain="college",
                verification_token=token,
                extra={"role": "college"},
            ),
            status=status.HTTP_201_CREATED,
        )


@password_reset_request_schema
class PasswordResetRequestView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, PasswordResetRequestThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = PasswordResetService().request_reset(**serializer.validated_data)
        data = {"message": "If the account exists, a reset link has been sent."}
        if token and AuthEmailService().expose_token_in_api():
            data["reset_token"] = token
        return self.success_response(data)


@password_reset_confirm_schema
class PasswordResetConfirmView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, OTPThrottle, EmailVerifyThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordResetService().confirm_reset(**serializer.validated_data)
        return self.success_response({"message": "Password updated successfully."})


@email_verify_schema
class EmailVerifyView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, OTPThrottle, EmailVerifyThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        EmailVerificationService().verify(**serializer.validated_data)
        return self.success_response({"message": "Email verified successfully."})


def _domain_for_user(user) -> str | None:
    domain = getattr(user, "domain", None)
    if domain in {"it", "professor", "college"}:
        return domain
    return None


@email_verify_schema
class ResendEmailVerifyView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, OTPThrottle, EmailVerifyThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = ResendEmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user if request.user.is_authenticated else None
        domain = data.get("domain") or (_domain_for_user(user) if user else None)
        email = data.get("email") or (getattr(user, "email", None) if user else None)
        if not domain:
            return self.error_response(
                "VALIDATION_ERROR", "domain is required when unauthenticated."
            )
        if not email:
            return self.error_response(
                "VALIDATION_ERROR", "email is required when unauthenticated."
            )
        try:
            EmailVerificationService().resend_verification(domain=domain, email=email)
        except Exception:
            pass
        return self.success_response(
            {"message": "If the account exists and is unverified, a new link was sent."}
        )


@logout_schema
class LogoutView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meta = {
            "ip_address": request.META.get("REMOTE_ADDR") or "",
            "user_agent": request.META.get("HTTP_USER_AGENT") or "",
        }
        LogoutService().logout(
            refresh_token=serializer.validated_data["refresh"], request_meta=meta
        )
        return self.success_response({"message": "Logged out successfully."})


@password_change_schema
class PasswordChangeView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [BruteForceIPThrottle, PasswordChangeThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        PasswordChangeService().change_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
            request=request,
        )
        return self.success_response({"message": "Password changed successfully."})


@me_schema
class MeView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(UserContextSelector().build_context(request.user))


@session_login_schema
class SessionLoginView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle, LoginIPThrottle, LoginEndpointThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request, domain):
        serializer = SessionLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = SessionService().login(
            request, domain=domain, **serializer.validated_data
        )
        return self.success_response(UserContextSelector().build_context(user))


@session_logout_schema
class SessionLogoutView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        SessionService().logout(request)
        return self.success_response({"message": "Session cleared."})


@user_lifecycle_schema
class UserActivationView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [BruteForceIPThrottle, AdminAuthThrottle]

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = UserActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = UserActivationService()
        if data["action"] == "activate":
            service.activate(domain=data["domain"], user_id=data["user_id"])
        elif data["action"] == "suspend":
            service.suspend(domain=data["domain"], user_id=data["user_id"])
        else:
            service.deactivate(domain=data["domain"], user_id=data["user_id"])
        return self.success_response(
            {"message": f"User {data['action']}d successfully."}
        )
