"""Web URL routes for IT Recruitment."""

from django.urls import path
from apps.it_recruitment.views.portal_redirects import (
    JobSeekerPortalEntryRedirectView,
    RecruiterPortalEntryRedirectView,
)

from apps.it_recruitment.views.auth import (
    ITJobSeekerLoginView,
    ITJobSeekerSignupView,
    ITLoginView,
    ITRecruiterLoginView,
    ITRecruiterSignupView,
    ITSignupCheckEmailView,
    ITSignupView,
)

urlpatterns = [
    path("login/", ITLoginView.as_view(), name="it_login"),
    path(
        "login/job-seeker/", ITJobSeekerLoginView.as_view(), name="it_login_job_seeker"
    ),
    path("login/recruiter/", ITRecruiterLoginView.as_view(), name="it_login_recruiter"),
    path("signup/", ITSignupView.as_view(), name="it_signup"),
    path(
        "signup/job-seeker/",
        ITJobSeekerSignupView.as_view(),
        name="it_signup_job_seeker",
    ),
    path(
        "signup/recruiter/", ITRecruiterSignupView.as_view(), name="it_signup_recruiter"
    ),
    path(
        "signup/check-email/",
        ITSignupCheckEmailView.as_view(),
        name="it_signup_check_email",
    ),
    path(
        "dashboard/job-seeker/",
        JobSeekerPortalEntryRedirectView.as_view(),
        name="it_job_seeker_dashboard",
    ),
    path(
        "dashboard/recruiter/",
        RecruiterPortalEntryRedirectView.as_view(),
        name="it_recruiter_dashboard",
    ),
]
