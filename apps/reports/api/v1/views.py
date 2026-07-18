from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from apps.authentication.permissions.throttles import ReportsAPIThrottle

from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.reports.services.analytics_service import AnalyticsService


class PlatformReportView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ReportsAPIThrottle]

    
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AnalyticsService().platform_overview())


class ITPipelineReportView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ReportsAPIThrottle]

    from drf_spectacular.utils import extend_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AnalyticsService().it_pipeline())


class FacultyPipelineReportView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ReportsAPIThrottle]

    from drf_spectacular.utils import extend_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AnalyticsService().faculty_pipeline())
