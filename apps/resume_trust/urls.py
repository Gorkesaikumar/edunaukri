"""URL configuration for Resume Trust & Fraud Detection Engine."""

from django.urls import path
from apps.resume_trust.views import (
    RecruiterResumeTrustReportAPIView,
    ResumeTrustAnalyzeAPIView,
    ResumeTrustHistoryAPIView,
    ResumeTrustProgressAPIView,
    ResumeTrustReportAPIView,
)

app_name = "resume_trust"

urlpatterns = [
    path("analyze/", ResumeTrustAnalyzeAPIView.as_view(), name="analyze"),
    path("progress/", ResumeTrustProgressAPIView.as_view(), name="progress"),
    path("report/", ResumeTrustReportAPIView.as_view(), name="report"),
    path("recruiter-report/", RecruiterResumeTrustReportAPIView.as_view(), name="recruiter_report"),
    path("history/", ResumeTrustHistoryAPIView.as_view(), name="history"),
]
