from django.urls import include, path

urlpatterns = [
    path("it/", include("apps.applications.api.v1.urls_it")),
    path("faculty/", include("apps.applications.api.v1.urls_faculty")),
    path("admin/", include("apps.applications.api.v1.urls_admin")),
]
