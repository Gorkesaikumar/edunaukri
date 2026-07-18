from django.urls import path

from apps.jobs.api.v1.views import (
    CompanyJobListView,
    JobArchiveView,
    JobCloseView,
    JobDashboardView,
    JobDetailView,
    JobDuplicateView,
    JobListCreateView,
    JobPauseView,
    JobPreviewView,
    JobPublishView,
    JobReopenView,
    JobStatisticsView,
    JobTemplateListView,
    JobUnpublishView,
    JobVisibilityView,
    PublicJobDetailView,
    PublicJobListView,
    RecruiterJobListView,
)
from apps.jobs.api.v1.views_admin import (
    AdminJobDashboardView,
    AdminJobDetailView,
    AdminJobListView,
    AdminJobRejectView,
)

urlpatterns = [
    # Admin oversight (before <uuid> routes)
    path("admin/", AdminJobListView.as_view(), name="admin-jobs"),
    path(
        "admin/dashboard/", AdminJobDashboardView.as_view(), name="admin-job-dashboard"
    ),
    path("admin/<uuid:job_id>/", AdminJobDetailView.as_view(), name="admin-job-detail"),
    path(
        "admin/<uuid:job_id>/reject/",
        AdminJobRejectView.as_view(),
        name="admin-job-reject",
    ),
    # Public discovery
    path("public/", PublicJobListView.as_view(), name="public-jobs"),
    path(
        "public/<uuid:job_id>/", PublicJobDetailView.as_view(), name="public-job-detail"
    ),
    # Recruiter dashboards / scoped lists
    path("mine/", RecruiterJobListView.as_view(), name="recruiter-jobs"),
    path("templates/", JobTemplateListView.as_view(), name="job-templates"),
    path("dashboard/", JobDashboardView.as_view(), name="job-dashboard"),
    path(
        "company/<uuid:company_id>/", CompanyJobListView.as_view(), name="company-jobs"
    ),
    # Core CRUD
    path("", JobListCreateView.as_view(), name="jobs"),
    path("<uuid:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("<uuid:job_id>/preview/", JobPreviewView.as_view(), name="job-preview"),
    path(
        "<uuid:job_id>/statistics/", JobStatisticsView.as_view(), name="job-statistics"
    ),
    path(
        "<uuid:job_id>/visibility/", JobVisibilityView.as_view(), name="job-visibility"
    ),
    # Lifecycle actions
    path("<uuid:job_id>/publish/", JobPublishView.as_view(), name="job-publish"),
    path("<uuid:job_id>/unpublish/", JobUnpublishView.as_view(), name="job-unpublish"),
    path("<uuid:job_id>/pause/", JobPauseView.as_view(), name="job-pause"),
    path("<uuid:job_id>/reopen/", JobReopenView.as_view(), name="job-reopen"),
    path("<uuid:job_id>/close/", JobCloseView.as_view(), name="job-close"),
    path("<uuid:job_id>/archive/", JobArchiveView.as_view(), name="job-archive"),
    path("<uuid:job_id>/duplicate/", JobDuplicateView.as_view(), name="job-duplicate"),
]
