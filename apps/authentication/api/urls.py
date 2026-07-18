from django.urls import path

from apps.authentication.api.v1.views import (
    EmailVerifyView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterCollegeUserView,
    RegisterITUserView,
    RegisterJobSeekerView,
    RegisterProfessorView,
    RegisterRecruiterView,
    ResendEmailVerifyView,
    SessionLoginView,
    SessionLogoutView,
    UserActivationView,
)

urlpatterns = [
    # Registration — separate IT vs Academic flows
    path("register/seeker/", RegisterJobSeekerView.as_view(), name="register-seeker"),
    path(
        "register/recruiter/",
        RegisterRecruiterView.as_view(),
        name="register-recruiter",
    ),
    path("register/it/", RegisterITUserView.as_view(), name="register-it"),
    path(
        "register/professor/",
        RegisterProfessorView.as_view(),
        name="register-professor",
    ),
    path(
        "register/college/", RegisterCollegeUserView.as_view(), name="register-college"
    ),
    # Password lifecycle
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    # Email verification framework
    path("email/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend/", ResendEmailVerifyView.as_view(), name="email-resend"),
    # JWT logout (refresh blacklist)
    path("logout/", LogoutView.as_view(), name="logout"),
    # Session auth (for future server-rendered login pages)
    path(
        "session/login/<str:domain>/", SessionLoginView.as_view(), name="session-login"
    ),
    path("session/logout/", SessionLogoutView.as_view(), name="session-logout"),
    # Profile initialization context
    path("me/", MeView.as_view(), name="auth-me"),
    # Admin user lifecycle
    path("admin/users/lifecycle/", UserActivationView.as_view(), name="user-lifecycle"),
]
