"""API URL router for Jobs. Mounted at /api/v1/jobs/."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.jobs.api.v1.urls")),
]
