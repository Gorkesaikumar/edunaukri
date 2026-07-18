from django.urls import include, path

urlpatterns = [
    path("", include("apps.invoices.api.v1.urls")),
]
