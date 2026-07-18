from drf_spectacular.utils import extend_schema
import io

from django.http import HttpResponse
from rest_framework import permissions

from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.reports.services.analytics_service import AnalyticsService
from apps.reports.services.export_service import ExportService


class PlatformExportView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    from drf_spectacular.utils import extend_schema, OpenApiParameter
    @extend_schema(parameters=[OpenApiParameter(name="export_as", type=str, required=False)], responses={200: dict})
    @extend_schema(responses={200: dict})
    def get(self, request):
        data = AnalyticsService().platform_overview()
        export_as = request.query_params.get("export_as", "json").lower()
        if export_as == "csv":
            rows = ExportService().flatten_dict(data)
            csv_text = ExportService().to_csv(rows, fieldnames=["metric", "value"])
            response = HttpResponse(csv_text, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="platform-report.csv"'
            )
            return response
        return self.success_response(data)


class ITPipelineExportView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    from drf_spectacular.utils import extend_schema, OpenApiParameter
    @extend_schema(parameters=[OpenApiParameter(name="export_as", type=str, required=False)], responses={200: dict})
    @extend_schema(responses={200: dict})
    def get(self, request):
        pipeline = AnalyticsService().it_pipeline()
        export_as = request.query_params.get("export_as", "json").lower()
        if export_as == "csv":
            rows = [{"status": k, "count": v} for k, v in pipeline.items()]
            csv_text = ExportService().to_csv(rows, fieldnames=["status", "count"])
            response = HttpResponse(csv_text, content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="it-pipeline.csv"'
            return response
        return self.success_response(pipeline)


class FacultyPipelineExportView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

    from drf_spectacular.utils import extend_schema, OpenApiParameter
    @extend_schema(parameters=[OpenApiParameter(name="export_as", type=str, required=False)], responses={200: dict})
    @extend_schema(responses={200: dict})
    def get(self, request):
        pipeline = AnalyticsService().faculty_pipeline()
        export_as = request.query_params.get("export_as", "json").lower()
        if export_as == "csv":
            rows = [{"status": k, "count": v} for k, v in pipeline.items()]
            csv_text = ExportService().to_csv(rows, fieldnames=["status", "count"])
            response = HttpResponse(csv_text, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="faculty-pipeline.csv"'
            )
            return response
        return self.success_response(pipeline)
