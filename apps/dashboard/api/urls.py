from django.urls import include, path

urlpatterns = [
    path("", include("apps.dashboard.api.v1.urls")),
]
