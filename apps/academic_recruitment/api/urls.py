from django.urls import include, path

urlpatterns = [
    path("", include("apps.academic_recruitment.api.v1.urls")),
]
