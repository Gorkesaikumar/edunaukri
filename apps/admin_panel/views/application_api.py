import logging
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from apps.admin_panel.views.web import SuperAdminPortalMixin
from apps.applications.models import JobApplication, FacultyApplication

logger = logging.getLogger(__name__)


class SuperAdminApplicationDetailAPIView(SuperAdminPortalMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            application_id = kwargs.get("application_id")
            domain = request.GET.get("domain", "it").lower()

            if domain == "faculty":
                app = get_object_or_404(
                    FacultyApplication.objects.select_related(
                        "professor__user", "vacancy", "college", "cv_file"
                    ).prefetch_related("status_history"),
                    pk=application_id,
                    is_deleted=False,
                )

                candidate = {
                    "id": str(app.professor.pk) if app.professor else "",
                    "name": app.applicant_name_snapshot,
                    "email": app.professor.user.email
                    if (app.professor and hasattr(app.professor, "user"))
                    else "",
                    "phone": getattr(
                        app.professor,
                        "phone_number",
                        getattr(app.professor.user, "phone_number", ""),
                    ),
                    "uuid": str(app.professor.pk) if app.professor else "",
                }

                job = {
                    "title": app.vacancy_title_snapshot,
                    "company": app.college_name_snapshot,
                    "domain": "FACULTY",
                    "recruiter": "",
                }

                resume_file = app.cv_file
                history_qs = app.status_history.all().order_by("-changed_at")

            else:
                app = get_object_or_404(
                    JobApplication.objects.select_related(
                        "job_seeker__user", "job_posting", "company", "resume_file"
                    ).prefetch_related("status_history"),
                    pk=application_id,
                    is_deleted=False,
                )

                candidate = {
                    "id": str(app.job_seeker.pk) if app.job_seeker else "",
                    "name": app.applicant_name_snapshot,
                    "email": app.job_seeker.user.email
                    if (app.job_seeker and hasattr(app.job_seeker, "user"))
                    else "",
                    "phone": getattr(
                        app.job_seeker,
                        "phone_number",
                        getattr(app.job_seeker.user, "phone_number", ""),
                    ),
                    "uuid": str(app.job_seeker.pk) if app.job_seeker else "",
                }

                job = {
                    "title": app.job_title_snapshot,
                    "company": app.company_name_snapshot,
                    "domain": "IT",
                    "recruiter": "",
                }

                resume_file = app.resume_file
                history_qs = app.status_history.all().order_by("-changed_at")

            # Construct Resume dict
            resume = None
            if resume_file:
                resume = {
                    "url": f"/media/{resume_file.storage_path}",
                    "filename": resume_file.original_filename,
                }

            # Construct History list
            history = []
            for h in history_qs:
                history.append(
                    {
                        "status": h.to_status.upper().replace("_", " "),
                        "date": h.changed_at.isoformat(),
                        "updated_by": "System" if not h.changed_by_id else "Admin",
                        "notes": h.notes,
                    }
                )

            application = {
                "id": str(app.pk),
                "status": app.status.upper().replace("_", " "),
                "applied_at": app.applied_at.isoformat() if app.applied_at else "",
                "rejection_reason": app.rejection_reason,
            }

            return JsonResponse(
                {
                    "success": True,
                    "application": application,
                    "candidate": candidate,
                    "job": job,
                    "resume": resume,
                    "history": history,
                }
            )
        except Exception as exc:
            logger.exception("Failed to fetch application detail")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)
