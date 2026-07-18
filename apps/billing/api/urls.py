from django.urls import include, path

urlpatterns = [
    path("", include("apps.billing.api.v1.urls")),
]
