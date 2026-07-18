from django.urls import path

from apps.reports.api.v1.export_views import (
    FacultyPipelineExportView,
    ITPipelineExportView,
    PlatformExportView,
)
from apps.reports.api.v1.views import (
    FacultyPipelineReportView,
    ITPipelineReportView,
    PlatformReportView,
)

urlpatterns = [
    path(
        "exports/platform/", PlatformExportView.as_view(), name="report-platform-export"
    ),
    path(
        "exports/it-pipeline/",
        ITPipelineExportView.as_view(),
        name="report-it-pipeline-export",
    ),
    path(
        "exports/faculty-pipeline/",
        FacultyPipelineExportView.as_view(),
        name="report-faculty-pipeline-export",
    ),
    path("platform/", PlatformReportView.as_view(), name="report-platform"),
    path("it/pipeline/", ITPipelineReportView.as_view(), name="report-it-pipeline"),
    path(
        "faculty/pipeline/",
        FacultyPipelineReportView.as_view(),
        name="report-faculty-pipeline",
    ),
]
