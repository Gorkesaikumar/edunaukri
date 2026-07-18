"""API v1 URL composition — mount domain API routers."""

from django.urls import include, path

from apps.accounts.views.tokens import (
    AdminTokenObtainPairView,
    CollegeTokenObtainPairView,
    DomainTokenRefreshView,
    FacultyTokenObtainPairView,
    ITTokenObtainPairView,
    ProfessorTokenObtainPairView,
)

app_name = "v1"

urlpatterns = [
    # Infrastructure
    path("health/", include("apps.health.urls")),
    # Authentication (JWT)
    path("auth/admin/token/", AdminTokenObtainPairView.as_view(), name="admin-token"),
    path("auth/it/token/", ITTokenObtainPairView.as_view(), name="it-token"),
    path(
        "auth/faculty/token/",
        FacultyTokenObtainPairView.as_view(),
        name="faculty-token",
    ),
    path(
        "auth/professor/token/",
        ProfessorTokenObtainPairView.as_view(),
        name="professor-token",
    ),
    path(
        "auth/college/token/",
        CollegeTokenObtainPairView.as_view(),
        name="college-token",
    ),
    path("auth/token/refresh/", DomainTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/", include("apps.authentication.api.urls")),
    path("accounts/", include("apps.accounts.api.urls")),
    # Domain APIs
    path("it/", include("apps.it_recruitment.api.urls")),
    path("companies/", include("apps.companies.api.urls")),
    path("jobs/", include("apps.jobs.api.urls")),
    path("colleges/", include("apps.colleges.api.urls")),
    path("applications/", include("apps.applications.api.urls")),
    path("faculty/", include("apps.academic_recruitment.api.urls")),
    path("faculty-vacancies/", include("apps.faculty.api.urls")),
    # Shared services
    path("search/", include("apps.search.api.urls")),
    path("billing/", include("apps.billing.api.urls")),
    path("invoices/", include("apps.invoices.api.urls")),
    path("guarantee-claims/", include("apps.guarantee_claims.api.urls")),
    path("dashboard/", include("apps.dashboard.api.urls")),
    path("reports/", include("apps.reports.api.urls")),
    path("documents/", include("apps.documents.api.urls")),
    path("audit/", include("apps.audit.api.urls")),
    path("admin/", include("apps.admin_panel.api.urls")),
    path("notifications/", include("apps.notifications.api.urls")),
]
