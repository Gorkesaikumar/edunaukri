"""Root web URL composition — public site and domain UI routes."""

from django.urls import include, path, re_path
from django.views.generic import RedirectView

from apps.authentication.views.web_auth import WebLogoutView
from apps.it_recruitment.views.portal_redirects import (
    JobSeekerLegacyRedirectView,
    JobSeekerPortalEntryRedirectView,
    RecruiterLegacyRedirectView,
    RecruiterPortalEntryRedirectView,
)
from apps.academic_recruitment.views.portal_redirects import (
    CollegePortalEntryRedirectView,
    ProfessorPortalEntryRedirectView,
)
from apps.admin_panel.views.auth import SuperAdminLoginView
from apps.admin_panel.views.portal_redirects import (
    SuperAdminLegacyRedirectView,
    SuperAdminPortalEntryRedirectView,
)
from config.web_views import (
    DomainSelectionView,
    HomeView,
    SignupDomainSelectionView,
    live_activity_feed,
    AboutView,
)

urlpatterns = [
    # Public marketing site
    path("", HomeView.as_view(), name="home"),
    path("about/", AboutView.as_view(), name="about"),
    path("sign-in/", DomainSelectionView.as_view(), name="domain_selection"),
    path(
        "get-started/",
        SignupDomainSelectionView.as_view(),
        name="signup_domain_selection",
    ),
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/img/favicon.svg", permanent=True),
        name="favicon",
    ),
    path("live-activity/", live_activity_feed, name="live_activity"),
    path("logout/", WebLogoutView.as_view(), name="logout"),
    path("jobs/", include("apps.jobs.urls.marketplace")),
    path("institutions/", include("apps.reports.urls.institutions")),
    # UUID-scoped portal areas (must be registered before legacy flat routes)
    path("jobseeker/<uuid:user_uuid>/", include("apps.it_recruitment.urls.jobseeker")),
    path("recruiter/<uuid:user_uuid>/", include("apps.it_recruitment.urls.recruiter")),
    path(
        "professor/<uuid:user_uuid>/",
        include("apps.academic_recruitment.urls.professor"),
    ),
    path(
        "college/<uuid:user_uuid>/", include("apps.academic_recruitment.urls.college")
    ),
    path("super-admin/<uuid:user_uuid>/", include("apps.admin_panel.urls_web")),
    # Legacy flat portal URLs — redirect to authenticated user's UUID scope
    path(
        "jobseeker/",
        JobSeekerPortalEntryRedirectView.as_view(),
        name="jobseeker_portal_entry",
    ),
    re_path(
        r"^jobseeker/(?P<legacy_path>.+)/$",
        JobSeekerLegacyRedirectView.as_view(),
        name="jobseeker_legacy_redirect",
    ),
    path(
        "recruiter/",
        RecruiterPortalEntryRedirectView.as_view(),
        name="recruiter_portal_entry",
    ),
    re_path(
        r"^recruiter/(?P<legacy_path>.+)/$",
        RecruiterLegacyRedirectView.as_view(),
        name="recruiter_legacy_redirect",
    ),
    path(
        "professor/",
        ProfessorPortalEntryRedirectView.as_view(),
        name="professor_portal_entry",
    ),
    path(
        "college/",
        CollegePortalEntryRedirectView.as_view(),
        name="college_portal_entry",
    ),
    path("super-admin/login/", SuperAdminLoginView.as_view(), name="super_admin_login"),
    path(
        "super-admin/",
        SuperAdminPortalEntryRedirectView.as_view(),
        name="super_admin_portal_entry",
    ),
    re_path(
        r"^super-admin/(?P<legacy_path>.+)/$",
        SuperAdminLegacyRedirectView.as_view(),
        name="super_admin_legacy_redirect",
    ),
    # Domain web routes
    path("api/resume-trust/", include("apps.resume_trust.urls")),
    path("it/", include("apps.it_recruitment.urls.web")),
    path("auth/", include("apps.authentication.urls.web")),
    path("faculty/", include("apps.academic_recruitment.urls.web")),
    # Billing & Claims web routes
    path("", include("apps.invoices.urls.web")),
    path("", include("apps.guarantee_claims.urls.web")),
    # path("dashboard/", include("apps.dashboard.urls.web")),
]
