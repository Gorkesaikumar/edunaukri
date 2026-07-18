"""Health check and comprehensive diagnostic monitoring API views."""

from django.conf import settings
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.core.views.base import EnvelopeAPIView
from apps.health.services.monitoring_service import SystemHealthMonitoringService


class LivenessView(EnvelopeAPIView):
    """Return 200 if the application process is running."""

    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(tags=["health"], summary="Liveness probe", responses={200: dict})
    def get(self, request):
        return self.success_response({"status": "healthy"})


class ReadinessView(EnvelopeAPIView):
    """Verify database, Redis, and Celery broker connectivity."""

    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(tags=["health"], summary="Readiness probe", responses={200: dict})
    def get(self, request):
        checks = {
            "database": self._check_database(),
            "redis": self._check_redis(),
            "celery": self._check_celery(),
        }
        status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"
        http_status = 200 if status == "healthy" else 503
        return self.success_response(
            {"status": status, "checks": checks}, status=http_status
        )

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return "ok"
        except Exception:
            return "error"

    def _check_redis(self):
        try:
            import redis

            client = redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
            client.ping()
            return "ok"
        except Exception:
            return "error"

    def _check_celery(self):
        try:
            from config.celery import app

            conn = app.connection()
            conn.ensure_connection(max_retries=1)
            conn.release()
            return "ok"
        except Exception:
            return "error"


class SystemDiagnosticsView(EnvelopeAPIView):
    """Full system diagnostics across CPU, RAM, Disk, Redis, Celery, Database, and Uptime."""

    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(tags=["health"], summary="Full system diagnostic metrics", responses={200: dict})
    def get(self, request):
        diagnostics = SystemHealthMonitoringService.collect_all_diagnostics()
        http_status = 200 if diagnostics["status"] in ("healthy", "degraded") else 503
        return self.success_response(diagnostics, status=http_status)


class SystemMonitoringAlertCheckView(EnvelopeAPIView):
    """Evaluate diagnostic metrics against configured thresholds and dispatch email alerts if breached."""

    permission_classes = [AllowAny]
    throttle_classes = []

    @extend_schema(tags=["health"], summary="Trigger threshold evaluation and email alerting", responses={200: dict})
    def get(self, request):
        report = SystemHealthMonitoringService.evaluate_thresholds_and_alert()
        http_status = 200 if report["overall_status"] != "unhealthy" else 503
        return self.success_response(report, status=http_status)
