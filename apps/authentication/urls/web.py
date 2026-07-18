"""Web URL routes for Authentication."""

from django.urls import path

from apps.authentication.views.oauth import (
    GoogleOAuthCallbackView,
    GoogleOAuthStartView,
    LinkedInOAuthCallbackView,
    LinkedInOAuthStartView,
)
from apps.authentication.views.web_auth import (
    WebLogoutView,
    WebSessionStatusView,
    WebTokenRefreshView,
)
from apps.authentication.views.web_email_verification import WebEmailVerificationView
from apps.authentication.views.web_password_reset import (
    WebForgotPasswordView,
    WebResetPasswordView,
)

urlpatterns = [
    path("google/", GoogleOAuthStartView.as_view(), name="oauth_google"),
    path(
        "google/callback/",
        GoogleOAuthCallbackView.as_view(),
        name="oauth_google_callback",
    ),
    path("linkedin/", LinkedInOAuthStartView.as_view(), name="oauth_linkedin"),
    path(
        "linkedin/callback/",
        LinkedInOAuthCallbackView.as_view(),
        name="oauth_linkedin_callback",
    ),
    path(
        "forgot-password/", WebForgotPasswordView.as_view(), name="web_forgot_password"
    ),
    path("reset-password/", WebResetPasswordView.as_view(), name="web_reset_password"),
    path("verify-email/", WebEmailVerificationView.as_view(), name="web_verify_email"),
    path("logout/", WebLogoutView.as_view(), name="web_logout"),
    path("session/status/", WebSessionStatusView.as_view(), name="web_session_status"),
    path("token/refresh/", WebTokenRefreshView.as_view(), name="web_token_refresh"),
]
