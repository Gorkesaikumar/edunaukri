"""API endpoints for Resume Trust & Fraud Detection Engine."""

from __future__ import annotations

import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from apps.core.exceptions.domain_exceptions import ValidationException
from apps.documents.models import StoredFile
from apps.resume_trust.models import FraudDomainType, ResumeFraudAnalysis
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService
from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService

# Analysis stage definitions — ordered list used by both backend and frontend
ANALYSIS_STAGES = [
    {"key": "UPLOAD_COMPLETED",       "label": "Resume uploaded successfully",             "pct": 12},
    {"key": "PDF_VALIDATED",           "label": "File integrity & PDF readability verified",  "pct": 24},
    {"key": "TEXT_EXTRACTED",          "label": "Text extracted from document",              "pct": 36},
    {"key": "RESUME_DETECTED",         "label": "Resume structure & layout detected",        "pct": 48},
    {"key": "AI_ANALYSIS_STARTED",     "label": "Identifying candidate information",          "pct": 57},
    {"key": "SKILLS_ANALYZED",         "label": "Detecting skills & technical stack",         "pct": 66},
    {"key": "EDUCATION_ANALYZED",      "label": "Detecting education & qualifications",       "pct": 72},
    {"key": "EXPERIENCE_ANALYZED",     "label": "Detecting work experience & projects",       "pct": 78},
    {"key": "TRUST_ANALYSIS_COMPLETED","label": "Performing Resume Trust Analysis",           "pct": 87},
    {"key": "MATCH_SCORE_COMPLETED",   "label": "Calculating Resume Match Score",             "pct": 93},
    {"key": "PROFILE_UPDATED",         "label": "Synchronizing profile information",          "pct": 96},
    {"key": "ANALYSIS_COMPLETED",      "label": "Analysis complete",                         "pct": 100},
]


def _unauthorized():
    return JsonResponse({"success": False, "error": "Authentication required."}, status=401)


def _determine_user_domain(user) -> tuple[int | None, str]:
    """Helper to extract candidate user_id and domain type from request.user."""
    if not user or not user.is_authenticated:
        return None, FraudDomainType.IT

    # Check if Professor User
    from apps.accounts.models.professor_user import ProfessorUser
    if isinstance(user, ProfessorUser) or getattr(user, "user_type", None) == "professor":
        return user.pk, FraudDomainType.FACULTY

    return user.pk, FraudDomainType.IT


@method_decorator(csrf_protect, name="dispatch")
class ResumeTrustAnalyzeAPIView(View):
    """POST /api/resume-trust/analyze/ — Manually trigger or execute a trust scan for a file."""

    def post(self, request, *args, **kwargs):
        user_id, domain = _determine_user_domain(request.user)
        if not user_id:
            return _unauthorized()

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
            file_id = body.get("file_id")
            stored_file = None
            parsed_data = body.get("parsed_data") or {}
            raw_text = body.get("raw_text", "")

            if file_id:
                stored_file = StoredFile.objects.filter(pk=file_id, is_deleted=False).first()

            # If raw_text was not provided, try to extract it from the stored file
            # (this is needed for "Refresh Analysis" calls that don't pass text)
            if stored_file and not raw_text:
                from apps.resume_trust.services.resume_trust_pipeline_service import ResumeTrustPipelineService
                raw_text = ResumeTrustPipelineService._extract_text_from_stored_file(stored_file)
                import logging as _l
                _l.getLogger("resume_trust").info(
                    "ResumeTrustAnalyzeAPIView: extracted %d chars from file %s", len(raw_text), file_id,
                )

            # If parsed_data is empty, pull from existing stored file extraction
            if stored_file and not parsed_data:
                from apps.it_recruitment.services.resume_parsing_service import ResumeParsingService
                parsed_data = ResumeParsingService().get_extracted(stored_file) or {}

            report = ResumeFraudDetectionService().initiate_analysis(
                seeker_user_id=user_id,
                domain=domain,
                stored_file=stored_file,
                parsed_data=parsed_data,
                raw_text=raw_text,
            )

            return JsonResponse({"success": True, "data": report, "report": report})
        except ValidationException as val_err:
            return JsonResponse({"success": False, "error": str(val_err)}, status=400)
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=500)




class ResumeTrustReportAPIView(View):
    """GET /api/resume-trust/report/ — Fetch latest trust & fraud report for authenticated candidate."""

    def get(self, request, *args, **kwargs):
        user_id, domain = _determine_user_domain(request.user)
        if not user_id:
            return _unauthorized()

        report = ResumeFraudReportService().get_user_latest_report(user_id, domain=domain)
        return JsonResponse({"success": True, "data": report, "report": report})


class ResumeTrustHistoryAPIView(View):
    """GET /api/resume-trust/history/ — Fetch trust score history timeline for authenticated candidate."""

    def get(self, request, *args, **kwargs):
        user_id, domain = _determine_user_domain(request.user)
        if not user_id:
            return _unauthorized()

        history_data = ResumeFraudReportService().get_user_trust_history(user_id, domain=domain)
        return JsonResponse({"success": True, "data": history_data, "history": history_data["history"]})


class RecruiterResumeTrustReportAPIView(View):
    """GET /api/resume-trust/recruiter-report/ — Fetch recruiter-friendly trust report with strict permission checks."""

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return _unauthorized()

        seeker_user_id = request.GET.get("user_id") or request.GET.get("seeker_user_id")
        domain = (request.GET.get("domain") or FraudDomainType.IT).lower()
        app_id = request.GET.get("application_id")

        # Application authorization check
        if app_id:
            if domain == FraudDomainType.FACULTY:
                from apps.applications.models import FacultyApplication
                from apps.applications.services.faculty_application_authorization_service import (
                    FacultyApplicationAuthorizationService,
                )
                from apps.core.exceptions.domain_exceptions import PermissionDeniedException

                app = FacultyApplication.objects.filter(pk=app_id, is_deleted=False).select_related("professor__user").first()
                if not app:
                    return JsonResponse({"success": False, "error": "Application not found."}, status=404)
                try:
                    FacultyApplicationAuthorizationService().ensure_can_view_faculty_application(app, request.user)
                except PermissionDeniedException:
                    return JsonResponse({"success": False, "error": "Permission denied."}, status=403)
                if app.professor:
                    seeker_user_id = app.professor.user_id
            else:
                from apps.applications.models import JobApplication
                from apps.applications.services.application_authorization_service import (
                    ApplicationAuthorizationService,
                )
                from apps.core.exceptions.domain_exceptions import PermissionDeniedException

                app = JobApplication.objects.filter(pk=app_id, is_deleted=False).select_related("job_seeker__user").first()
                if not app:
                    return JsonResponse({"success": False, "error": "Application not found."}, status=404)
                try:
                    ApplicationAuthorizationService().ensure_can_view_it_application(app, request.user)
                except PermissionDeniedException:
                    return JsonResponse({"success": False, "error": "Permission denied."}, status=403)
                if app.job_seeker:
                    seeker_user_id = app.job_seeker.user_id

        if not seeker_user_id:
            return JsonResponse({"success": False, "error": "user_id or application_id parameter required."}, status=400)

        try:
            report = ResumeFraudReportService().get_recruiter_trust_report(int(seeker_user_id), domain=domain)
            return JsonResponse({"success": True, "data": report, "report": report})
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=500)


class ResumeTrustProgressAPIView(View):
    """GET /api/resume-trust/progress/ — Real-time analysis stage & percentage for the progress modal."""

    def get(self, request, *args, **kwargs):
        user_id, domain = _determine_user_domain(request.user)
        if not user_id:
            return _unauthorized()

        # Fetch the most-recent analysis for this user (any status)
        analysis = (
            ResumeFraudAnalysis.objects.filter(seeker_user_id=str(user_id), domain=domain)
            .order_by("-created_at")
            .first()
        )

        if not analysis:
            return JsonResponse({
                "success": True,
                "status": "NO_ANALYSIS",
                "percentage": 0,
                "stages": ANALYSIS_STAGES,
                "completed_keys": [],
                "current_stage": None,
                "error_message": None,
                "trust_score": None,
                "risk_level": None,
                "created_at_ms": None,
            })

        db_status = (analysis.status or "PENDING").upper()
        created_at_ms = int(analysis.created_at.timestamp() * 1000) if analysis.created_at else None

        if db_status == "FAILED":
            return JsonResponse({
                "success": True,
                "status": "FAILED",
                "percentage": 0,
                "stages": ANALYSIS_STAGES,
                "completed_keys": [],
                "current_stage": None,
                "error_message": analysis.error_message or "Resume analysis could not be completed.",
                "trust_score": None,
                "risk_level": None,
                "created_at_ms": created_at_ms,
            })

        if db_status in ("SUCCESS", "COMPLETED"):
            return JsonResponse({
                "success": True,
                "status": "COMPLETED",
                "percentage": 100,
                "stages": ANALYSIS_STAGES,
                "completed_keys": [s["key"] for s in ANALYSIS_STAGES],
                "current_stage": "ANALYSIS_COMPLETED",
                "error_message": None,
                "trust_score": analysis.trust_score,
                "risk_level": analysis.risk_level,
                "created_at_ms": created_at_ms,
            })

        # PENDING / PROCESSING — derive stage completion from elapsed seconds
        import time as _time
        from django.utils import timezone as _tz
        elapsed = (_tz.now() - analysis.created_at).total_seconds()

        completed_keys = []
        for stage in ANALYSIS_STAGES:
            # Map each stage to a rough elapsed-time window proportional to the percentage
            threshold = (stage["pct"] / 100.0) * 28  # expect ~28 s total
            if elapsed >= threshold:
                completed_keys.append(stage["key"])

        # Determine current active stage (first non-completed)
        remaining = [s for s in ANALYSIS_STAGES if s["key"] not in completed_keys]
        current_stage = remaining[0]["key"] if remaining else ANALYSIS_STAGES[-1]["key"]
        percentage = int((len(completed_keys) / len(ANALYSIS_STAGES)) * 100)

        return JsonResponse({
            "success": True,
            "status": "PROCESSING",
            "percentage": percentage,
            "stages": ANALYSIS_STAGES,
            "completed_keys": completed_keys,
            "current_stage": current_stage,
            "error_message": None,
            "trust_score": None,
            "risk_level": None,
        })


