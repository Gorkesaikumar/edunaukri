"""API URL router for Faculty Vacancies. Mounted at /api/v1/faculty-vacancies/."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.faculty.api.v1.urls")),
]
