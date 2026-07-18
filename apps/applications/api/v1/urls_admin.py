from django.urls import path

from apps.applications.api.v1.views_admin import (
    AdminFacultyApplicationDetailView,
    AdminFacultyApplicationHistoryView,
    AdminFacultyApplicationListView,
    AdminFacultyApplicationStatusView,
    AdminJobApplicationDetailView,
    AdminJobApplicationHistoryView,
    AdminJobApplicationListView,
    AdminJobApplicationStatusView,
)

urlpatterns = [
    path("it/", AdminJobApplicationListView.as_view(), name="admin-job-applications"),
    path(
        "it/<uuid:application_id>/",
        AdminJobApplicationDetailView.as_view(),
        name="admin-job-application-detail",
    ),
    path(
        "it/<uuid:application_id>/status/",
        AdminJobApplicationStatusView.as_view(),
        name="admin-job-application-status",
    ),
    path(
        "it/<uuid:application_id>/history/",
        AdminJobApplicationHistoryView.as_view(),
        name="admin-job-application-history",
    ),
    path(
        "faculty/",
        AdminFacultyApplicationListView.as_view(),
        name="admin-faculty-applications",
    ),
    path(
        "faculty/<uuid:application_id>/",
        AdminFacultyApplicationDetailView.as_view(),
        name="admin-faculty-application-detail",
    ),
    path(
        "faculty/<uuid:application_id>/status/",
        AdminFacultyApplicationStatusView.as_view(),
        name="admin-faculty-application-status",
    ),
    path(
        "faculty/<uuid:application_id>/history/",
        AdminFacultyApplicationHistoryView.as_view(),
        name="admin-faculty-application-history",
    ),
]
