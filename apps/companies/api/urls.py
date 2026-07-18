"""API URL router for Companies. Mounted at /api/v1/companies/."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.companies.api.v1.urls")),
]
