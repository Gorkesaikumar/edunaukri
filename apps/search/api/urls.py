from django.urls import include, path

urlpatterns = [
    path("", include("apps.search.api.v1.urls")),
]
