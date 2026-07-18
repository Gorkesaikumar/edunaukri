"""API URL router for Colleges. Mounted at /api/v1/colleges/."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.colleges.api.v1.urls")),
]
