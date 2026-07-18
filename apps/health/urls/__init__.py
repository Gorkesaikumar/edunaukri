"""Health check and diagnostic web routes."""

from django.urls import path

from apps.health.views import (
    LivenessView,
    ReadinessView,
    SystemDiagnosticsView,
    SystemMonitoringAlertCheckView,
)

app_name = "health"

urlpatterns = [
    path("", LivenessView.as_view(), name="liveness"),
    path("ready/", ReadinessView.as_view(), name="readiness"),
    path("metrics/", SystemDiagnosticsView.as_view(), name="metrics"),
    path("status/", SystemDiagnosticsView.as_view(), name="status"),
    path("check-alerts/", SystemMonitoringAlertCheckView.as_view(), name="check_alerts"),
]
