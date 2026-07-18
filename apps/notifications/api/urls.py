from django.urls import include, path

urlpatterns = [
    path("", include("apps.notifications.api.v1.urls")),
]
