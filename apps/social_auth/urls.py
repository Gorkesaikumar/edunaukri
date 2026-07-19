"""URL configuration for the Social Auth app.

Routes
------
Provider        Endpoint                    View                    Name
--------        --------                    ----                    ----
Google          /auth/google/login/         GoogleLoginView         google-login
Google          /auth/google/callback/      GoogleCallbackView      google-callback

LinkedIn        /auth/linkedin/login/       LinkedInLoginView       linkedin-login      * next implementation
LinkedIn        /auth/linkedin/callback/    LinkedInCallbackView    linkedin-callback   * next implementation

Microsoft       /auth/microsoft/login/      MicrosoftLoginView      microsoft-login     * future
Microsoft       /auth/microsoft/callback/   MicrosoftCallbackView   microsoft-callback  * future

GitHub          /auth/github/login/         GitHubLoginView         github-login        * future
GitHub          /auth/github/callback/      GitHubCallbackView      github-callback     * future
"""

from __future__ import annotations

from django.urls import path

from apps.social_auth import views

app_name = "social_auth"

urlpatterns = [
    # ------------------------------------------------------------------
    # Google
    # ------------------------------------------------------------------
    path(
        "google/login/",
        views.GoogleLoginView.as_view(),
        name="google-login",
    ),
    path(
        "google/callback/",
        views.GoogleCallbackView.as_view(),
        name="google-callback",
    ),
    # ------------------------------------------------------------------
    # LinkedIn (uncomment after implementing LinkedInLoginView and
    # LinkedInCallbackView in views.py)
    # ------------------------------------------------------------------
    # path(
    #     "auth/linkedin/login/",
    #     views.LinkedInLoginView.as_view(),
    #     name="linkedin-login",
    # ),
    # path(
    #     "auth/linkedin/callback/",
    #     views.LinkedInCallbackView.as_view(),
    #     name="linkedin-callback",
    # ),
    # ------------------------------------------------------------------
    # Microsoft (future provider — uncomment after implementing views)
    # ------------------------------------------------------------------
    # path(
    #     "auth/microsoft/login/",
    #     views.MicrosoftLoginView.as_view(),
    #     name="microsoft-login",
    # ),
    # path(
    #     "auth/microsoft/callback/",
    #     views.MicrosoftCallbackView.as_view(),
    #     name="microsoft-callback",
    # ),
    # ------------------------------------------------------------------
    # GitHub (future provider — uncomment after implementing views)
    # ------------------------------------------------------------------
    # path(
    #     "auth/github/login/",
    #     views.GitHubLoginView.as_view(),
    #     name="github-login",
    # ),
    # path(
    #     "auth/github/callback/",
    #     views.GitHubCallbackView.as_view(),
    #     name="github-callback",
    # ),
]
