from django.urls import include, path

urlpatterns = [
    path("", include("apps.documents.api.v1.urls")),
]
