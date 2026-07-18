from django.urls import include, path

urlpatterns = [
    path("", include("apps.guarantee_claims.api.v1.urls")),
]
