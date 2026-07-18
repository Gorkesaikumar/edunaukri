from django.urls import include, path

urlpatterns = [
    path("", include("apps.admin_panel.api.v1.urls")),
]
