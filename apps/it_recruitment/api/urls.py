from django.urls import include, path

urlpatterns = [
    path("", include("apps.it_recruitment.api.v1.urls")),
]
