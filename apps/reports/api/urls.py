from django.urls import include, path

urlpatterns = [
    path("", include("apps.reports.api.v1.urls")),
]
