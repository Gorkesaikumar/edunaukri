from django.urls import path

from apps.audit.api.v1.views import AuditEventListView

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-events"),
]
