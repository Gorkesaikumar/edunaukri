from django.urls import path

from apps.dashboard.api.v1.views import (
    AdminDashboardView,
    CollegeDashboardView,
    ProfessorDashboardView,
    RecruiterDashboardView,
    SeekerDashboardView,
)

urlpatterns = [
    path("seeker/", SeekerDashboardView.as_view(), name="dashboard-seeker"),
    path("recruiter/", RecruiterDashboardView.as_view(), name="dashboard-recruiter"),
    path("professor/", ProfessorDashboardView.as_view(), name="dashboard-professor"),
    path("college/", CollegeDashboardView.as_view(), name="dashboard-college"),
    path("admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
]
