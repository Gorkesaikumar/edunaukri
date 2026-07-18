from django.urls import path

from apps.notifications.api.v1.views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationTrackerMarkReadView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications"),
    path(
        "tracker/mark-read/",
        NotificationTrackerMarkReadView.as_view(),
        name="notification-tracker-read",
    ),
    path(
        "<uuid:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="notification-read",
    ),
]
