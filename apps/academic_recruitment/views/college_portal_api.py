"""Institution portal web APIs — vacancies, applications, and institution profile."""

from __future__ import annotations

import json
from typing import Callable

from django.http import FileResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.db import transaction

from apps.accounts.models.college_user import CollegeUser
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.applications.services.recruitment_workflow_service import RecruitmentWorkflowService
from apps.applications.constants.faculty_enums import FacultyApplicationStatus
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.colleges.services.institution_service import InstitutionService
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    DomainException,
    PermissionDeniedException,
    ValidationException,
)
from apps.documents.services.storage_service import StorageService
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.faculty.services.faculty_vacancy_service import FacultyVacancyService
from apps.faculty.services.vacancy_lifecycle_service import FacultyLifecycleService
from apps.faculty.services.vacancy_publication_service import FacultyPublicationService

from apps.academic_recruitment.services.college_application_detail_portal_service import (
    CollegeApplicationDetailPortalService,
)
from apps.academic_recruitment.services.college_applications_portal_service import (
    CollegeApplicationsPortalService,
)
from apps.academic_recruitment.services.college_interview_portal_service import (
    CollegeInterviewPortalService,
)
from apps.academic_recruitment.services.college_profile_portal_service import (
    CollegeProfilePortalService,
)
from apps.academic_recruitment.services.college_vacancies_portal_service import (
    CollegeVacanciesPortalService,
)
from apps.academic_recruitment.views.college_api_base import CollegeScopedAPIView


def _forbidden():
    return JsonResponse({"success": False, "error": "Forbidden."}, status=403)


def _error_response(exc):
    if isinstance(exc, (ValidationException, BusinessLogicException, DomainException)):
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    return JsonResponse({"success": False, "error": str(exc)}, status=400)


def _authorized(request) -> CollegeUser | None:
    if not isinstance(request.user, CollegeUser):
        return None
    return request.user


def _parse_json(request) -> dict:
    return json.loads(request.body.decode("utf-8") or "{}")


def _get_vacancy(user: CollegeUser, vacancy_id) -> FacultyVacancy | None:
    return FacultyVacancySelector().for_college_user(user).filter(pk=vacancy_id).first()


def _get_application(user: CollegeUser, application_id):
    application = FacultyApplicationSelector().get_active(application_id)
    if not application:
        return None
    try:
        ApplicationAuthorizationService().ensure_can_view_faculty_application(
            application, user
        )
    except PermissionDeniedException:
        return None
    return application


def _vacancy_action_view(
    action: Callable[[FacultyVacancy, CollegeUser], FacultyVacancy],
    success_message: str,
):
    @method_decorator(csrf_protect, name="dispatch")
    class _View(CollegeScopedAPIView):
        http_method_names = ["post"]

        def post(self, request, vacancy_id):
            user = _authorized(request)
            if not user:
                return _forbidden()
            vacancy = _get_vacancy(user, vacancy_id)
            if not vacancy:
                return JsonResponse(
                    {"success": False, "error": "Vacancy not found."}, status=404
                )
            
            # Enforce Profile Completion for specific actions
            if action in (_publish, _reopen):
                from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
                completion_state = CollegeProfileCompletionService().get_dashboard_state(vacancy.college, user)
                if completion_state.percentage < 100:
                    return JsonResponse(
                        {"success": False, "error": "Complete your institution profile first to publish vacancies."}, status=400
                    )
            
            try:
                action(vacancy, user)
                return JsonResponse({"success": True, "message": success_message})
            except (
                ValidationException,
                BusinessLogicException,
                DomainException,
            ) as exc:
                return _error_response(exc)

    return _View


@method_decorator(csrf_protect, name="dispatch")
class CollegeInstitutionAPIView(CollegeScopedAPIView):
    def get(self, request):
        user = _authorized(request)
        if not user:
            return _forbidden()
        ctx = CollegeProfilePortalService().build(user)
        return JsonResponse({"success": True, "data": ctx.institution})

    def patch(self, request):
        user = _authorized(request)
        if not user:
            return _forbidden()
        membership = (
            CollegeMemberSelector()
            .for_user(user)
            .select_related("college")
            .order_by("-is_primary")
            .first()
        )
        if not membership:
            return JsonResponse(
                {"success": False, "error": "No institution found."}, status=404
            )
        try:
            data = _parse_json(request)
            allowed = {
                k: data[k]
                for k in (
                    "name",
                    "legal_name",
                    "description",
                    "vision",
                    "mission",
                    "institution_type",
                    "ownership_type",
                    "established_year",
                    "accreditation",
                    "naac_grade",
                    "number_of_faculty",
                    "number_of_students",
                    "address_line",
                    "city",
                    "state",
                    "pin_code",
                    "contact_email",
                    "contact_phone",
                    "website_url",
                    "linkedin_url",
                    "twitter_url",
                    "facebook_url",
                    "instagram_url",
                    "youtube_url",
                )
                if k in data
            }

            # Sanitize integer fields that might be empty strings from frontend formData
            for int_field in [
                "established_year",
                "number_of_faculty",
                "number_of_students",
            ]:
                if int_field in allowed:
                    if allowed[int_field] == "":
                        allowed[int_field] = None
                    elif allowed[int_field] is not None:
                        try:
                            allowed[int_field] = int(allowed[int_field])
                        except ValueError:
                            return JsonResponse(
                                {
                                    "success": False,
                                    "error": f"Invalid value for {int_field}.",
                                },
                                status=400,
                            )

            InstitutionService().update_institution(
                institution=membership.college, college_user=user, data=allowed
            )
            
            # Refresh instance to get updated fields before recalculating
            membership.college.refresh_from_db()
            
            # Recalculate profile completion
            from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
            CollegeProfileCompletionService().recalculate(membership.college, user)
            
            ctx = CollegeProfilePortalService().build(user)
            return JsonResponse(
                {
                    "success": True,
                    "message": "Institution updated.",
                    "data": ctx.institution,
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)
        except Exception as exc:
            import logging

            logging.getLogger(__name__).exception(
                "Unhandled exception in CollegeInstitutionAPIView"
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "An unexpected error occurred while saving the profile.",
                },
                status=500,
            )


@method_decorator(csrf_protect, name="dispatch")
class CollegeInstitutionImageUploadAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, image_type):
        user = _authorized(request)
        if not user:
            return _forbidden()

        if image_type not in ["logo", "banner"]:
            return JsonResponse(
                {"success": False, "error": "Invalid image type."}, status=400
            )

        if "image" not in request.FILES:
            return JsonResponse(
                {"success": False, "error": "No image uploaded."}, status=400
            )

        image_file = request.FILES["image"]

        membership = (
            CollegeMemberSelector()
            .for_user(user)
            .select_related("college")
            .order_by("-is_primary")
            .first()
        )
        if not membership:
            return JsonResponse(
                {"success": False, "error": "No institution found."}, status=404
            )

        try:
            from apps.documents.services.storage_service import StorageService
            from apps.documents.constants.enums import StorageFileType
            from apps.core.constants.enums import DomainType, EntityReferenceType

            storage = StorageService()
            file_type = (
                StorageFileType.COLLEGE_LOGO
                if image_type == "logo"
                else StorageFileType.COLLEGE_BANNER
            )

            stored_file = storage.upload(
                uploaded_file=image_file,
                domain=DomainType.FACULTY,
                file_type=file_type,
                owner_type=EntityReferenceType.FACULTY_COLLEGE,
                owner_id=membership.college.pk,
                uploaded_by_id=user.pk,
            )

            if image_type == "logo":
                membership.college.logo_file = stored_file
                membership.college.save(update_fields=["logo_file"])
            elif image_type == "banner":
                membership.college.cover_banner_file = stored_file
                membership.college.save(update_fields=["cover_banner_file"])

            membership.college.refresh_from_db()
            
            # Recalculate profile completion
            from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
            CollegeProfileCompletionService().recalculate(membership.college, user)

            from apps.it_recruitment.services.jobseeker_portal_helpers import media_url

            url = media_url(stored_file)

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Institution {image_type} updated successfully.",
                    "url": url,
                }
            )
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)


@method_decorator(csrf_protect, name="dispatch")
class CollegeVacanciesListAPIView(CollegeScopedAPIView):
    http_method_names = ["get"]

    def get(self, request):
        user = _authorized(request)
        if not user:
            return _forbidden()
        status = (request.GET.get("status") or "").strip()
        q = (request.GET.get("q") or "").strip()
        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        ctx = CollegeVacanciesPortalService().build(
            user, status_filter=status, q=q, page=page
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "vacancies": ctx.vacancies,
                    "stats": ctx.stats,
                    "pagination": ctx.pagination,
                    "filters": ctx.filters,
                },
            }
        )


def _publish(vacancy, user):
    FacultyPublicationService().publish(vacancy=vacancy, college_user=user)
    return vacancy


def _pause(vacancy, user):
    FacultyLifecycleService().pause(vacancy=vacancy, college_user=user)
    return vacancy


def _close(vacancy, user):
    FacultyLifecycleService().close(vacancy=vacancy, college_user=user)
    return vacancy


def _reopen(vacancy, user):
    FacultyLifecycleService().reopen(vacancy=vacancy, college_user=user)
    return vacancy


def _archive(vacancy, user):
    FacultyLifecycleService().archive(vacancy=vacancy, college_user=user)
    return vacancy


CollegeVacancyPublishAPIView = _vacancy_action_view(_publish, "Vacancy published.")
CollegeVacancyPauseAPIView = _vacancy_action_view(_pause, "Vacancy paused.")
CollegeVacancyCloseAPIView = _vacancy_action_view(_close, "Vacancy closed.")
CollegeVacancyReopenAPIView = _vacancy_action_view(_reopen, "Vacancy reopened.")
CollegeVacancyArchiveAPIView = _vacancy_action_view(_archive, "Vacancy archived.")


@method_decorator(csrf_protect, name="dispatch")
class CollegeVacancyDuplicateAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, vacancy_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        vacancy = _get_vacancy(user, vacancy_id)
        if not vacancy:
            return JsonResponse(
                {"success": False, "error": "Vacancy not found."}, status=404
            )

        # Enforce Profile Completion
        from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
        completion_state = CollegeProfileCompletionService().get_dashboard_state(vacancy.college, user)
        if completion_state.percentage < 100:
            return JsonResponse(
                {"success": False, "error": "Complete your institution profile first to duplicate vacancies."}, status=400
            )

        try:
            clone = FacultyVacancyService().duplicate_vacancy(
                vacancy=vacancy, college_user=user
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Vacancy duplicated.",
                    "data": {"id": str(clone.pk)},
                }
            )
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class CollegeVacancyDeleteAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, vacancy_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        vacancy = _get_vacancy(user, vacancy_id)
        if not vacancy:
            return JsonResponse(
                {"success": False, "error": "Vacancy not found."}, status=404
            )
        try:
            FacultyVacancyService().soft_delete(vacancy=vacancy, college_user=user)
            return JsonResponse({"success": True, "message": "Vacancy deleted."})
        except (ValidationException, BusinessLogicException, DomainException) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class CollegeApplicationsListAPIView(CollegeScopedAPIView):
    http_method_names = ["get"]

    def get(self, request):
        user = _authorized(request)
        if not user:
            return _forbidden()
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        vacancy_id = (request.GET.get("vacancy_id") or "").strip()
        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        ctx = CollegeApplicationsPortalService().build(
            user, q=q, status=status, vacancy_id=vacancy_id, page=page
        )
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "applications": ctx.applications,
                    "stats": ctx.stats,
                    "pagination": ctx.pagination,
                    "filters": ctx.filters,
                },
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class CollegeApplicationStatusAPIView(CollegeScopedAPIView):
    http_method_names = ["patch", "post"]

    def patch(self, request, application_id):
        return self._update(request, application_id)

    def post(self, request, application_id):
        return self._update(request, application_id)

    def _update(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request)
            new_status = (data.get("status") or "").strip()
            notes = (data.get("notes") or "").strip()
            rejection_reason = (data.get("rejection_reason") or "").strip()
            if not new_status:
                return JsonResponse(
                    {"success": False, "error": "Status is required."}, status=400
                )
            
            # Enforce rejection business rules: only block when interview is actively scheduled
            if new_status == FacultyApplicationStatus.REJECTED:
                blocked_rejection_stages = {
                    FacultyApplicationStatus.INTERVIEW_SCHEDULED,
                }
                if application.status in blocked_rejection_stages:
                    return JsonResponse(
                        {"success": False, "error": "Cancel the scheduled interview before rejecting the candidate."}, status=400
                    )

            FacultyApplicationService().update_status_for_actor(
                application,
                new_status,
                notes,
                actor=user,
                rejection_reason=rejection_reason,
            )
            return JsonResponse(
                {"success": True, "message": "Application status updated."}
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


class CollegeApplicationProfileModalAPIView(CollegeScopedAPIView):
    http_method_names = ["get"]

    def get(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        detail = CollegeApplicationDetailPortalService().get_detail(
            user, application_id
        )
        if not detail:
            return JsonResponse({"success": False, "error": "Application not found."}, status=404)
        
        html = render_to_string(
            "academic/college/applications/profile_modal_content.html",
            {"application_detail": detail},
            request=request,
        )
        return JsonResponse({"success": True, "html": html})


@method_decorator(csrf_protect, name="dispatch")
class CollegeApplicationNotesAPIView(CollegeScopedAPIView):
    http_method_names = ["patch", "post"]

    def patch(self, request, application_id):
        return self._update(request, application_id)

    def post(self, request, application_id):
        return self._update(request, application_id)

    def _update(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request)
            svc = FacultyApplicationService()
            if "college_notes" in data:
                svc.add_college_notes(
                    application, notes=data.get("college_notes") or "", actor=user
                )
            if "internal_remarks" in data:
                svc.add_internal_remarks(
                    application, remarks=data.get("internal_remarks") or "", actor=user
                )
            if "college_rating" in data:
                raw_rating = data.get("college_rating")
                rating = None
                if raw_rating not in (None, ""):
                    rating = int(raw_rating)
                svc.add_college_rating(application, rating=rating, actor=user)
            return JsonResponse({"success": True, "message": "Notes saved."})
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


class CollegeApplicationCvAPIView(CollegeScopedAPIView):
    http_method_names = ["get"]

    def get(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        stored = application.cv_file
        if not stored and application.professor_id and application.professor.cv_file_id:
            stored = application.professor.cv_file
        if not stored:
            return JsonResponse(
                {"success": False, "error": "CV not available for this application."},
                status=404,
            )
        try:
            path = StorageService().get_absolute_path(stored)
            inline = request.GET.get("preview") == "1"
            response = FileResponse(path.open("rb"), filename=stored.original_filename)
            disposition = "inline" if inline else "attachment"
            response["Content-Disposition"] = (
                f'{disposition}; filename="{stored.original_filename}"'
            )
            return response
        except FileNotFoundError:
            return JsonResponse(
                {"success": False, "error": "CV file missing from storage."}, status=404
            )


@method_decorator(csrf_protect, name="dispatch")
class CollegeInterviewsListAPIView(CollegeScopedAPIView):
    http_method_names = ["get"]

    def get(self, request):
        user = _authorized(request)
        if not user:
            return _forbidden()
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        try:
            page = max(1, int(request.GET.get("page") or 1))
        except ValueError:
            page = 1
        ctx = CollegeInterviewPortalService().build(user, page=page, q=q, status=status)
        return JsonResponse(
            {
                "success": True,
                "data": {
                    "interviews": ctx.interviews,
                    "pending_candidates": ctx.pending_candidates,
                    "summary": ctx.summary,
                    "calendar_events": ctx.calendar_events,
                    "filters": ctx.filters,
                    "page": ctx.page,
                    "total_pages": ctx.total_pages,
                    "total_count": ctx.total_count,
                },
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class CollegeInterviewScheduleAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request)
            CollegeInterviewPortalService().schedule_interview(
                actor=user,
                application=application,
                scheduled_at_raw=(data.get("scheduled_at") or "").strip(),
                interview_type=(data.get("interview_type") or "").strip(),
                mode=(data.get("mode") or "").strip(),
                meeting_platform=(data.get("meeting_platform") or "").strip(),
                meet_url=(data.get("meet_url") or "").strip(),
                location=(data.get("location") or "").strip(),
                interviewer_name=(data.get("interviewer_name") or "").strip(),
                notes=(data.get("notes") or "").strip(),
                duration_minutes=int(data.get("duration_minutes") or 45),
            )
            return JsonResponse({"success": True, "message": "Interview scheduled."})
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class CollegeInterviewRescheduleAPIView(CollegeScopedAPIView):
    http_method_names = ["patch"]

    def patch(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request)
            CollegeInterviewPortalService().schedule_interview(
                actor=user,
                application=application,
                scheduled_at_raw=(data.get("scheduled_at") or "").strip(),
                interview_type=(data.get("interview_type") or "").strip(),
                mode=(data.get("mode") or "").strip(),
                meeting_platform=(data.get("meeting_platform") or "").strip(),
                meet_url=(data.get("meet_url") or "").strip(),
                location=(data.get("location") or "").strip(),
                interviewer_name=(data.get("interviewer_name") or "").strip(),
                notes=(
                    data.get("notes") or "Interview rescheduled by institution."
                ).strip(),
                duration_minutes=int(data.get("duration_minutes") or 45),
            )
            return JsonResponse({"success": True, "message": "Interview rescheduled."})
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class CollegeInterviewCompleteAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            import json
            data = json.loads(request.body) if request.body else {}
            from apps.applications.services.recruitment_workflow_service import RecruitmentWorkflowService
            RecruitmentWorkflowService().complete_interview_with_evaluation(
                domain="faculty",
                application_id=application_id,
                actor=user,
                data=data
            )
            return JsonResponse(
                {"success": True, "message": "Interview marked completed with evaluation saved."}
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)


@method_decorator(csrf_protect, name="dispatch")
class CollegeInterviewCancelAPIView(CollegeScopedAPIView):
    http_method_names = ["post"]

    def post(self, request, application_id):
        user = _authorized(request)
        if not user:
            return _forbidden()
        application = _get_application(user, application_id)
        if not application:
            return JsonResponse(
                {"success": False, "error": "Application not found."}, status=404
            )
        try:
            data = _parse_json(request) if request.body else {}
            CollegeInterviewPortalService().cancel_interview(
                actor=user,
                application=application,
                reason=(data.get("reason") or "").strip(),
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Interview cancelled and moved to pending scheduling.",
                }
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {"success": False, "error": "Invalid JSON."}, status=400
            )
        except ValueError as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=400)
        except (
            ValidationException,
            BusinessLogicException,
            DomainException,
            PermissionDeniedException,
        ) as exc:
            return _error_response(exc)

from apps.notifications.models import Notification

class CollegeNotificationsPollAPIView(CollegeScopedAPIView):
    """Lightweight endpoint for real-time polling of new unread applications."""
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        # Only fetch unread NEW_FACULTY_APPLICATION notifications for this recruiter
        qs = Notification.objects.filter(
            recipient_domain="college",
            recipient_id=request.user.pk,
            event_type="NEW_FACULTY_APPLICATION",
            is_read=False,
        ).order_by("-created_at")

        unread_count = qs.count()

        recent_notifications = []
        if unread_count > 0:
            for notif in qs[:5]:  # Limit to 5 for popup summary
                recent_notifications.append(
                    {
                        "candidate_name": notif.payload.get("candidate_name"),
                        "vacancy_name": notif.payload.get("vacancy_name"),
                        "timestamp": notif.created_at.isoformat(),
                    }
                )

        return JsonResponse(
            {
                "unread_applications_count": unread_count,
                "recent_applications": recent_notifications,
            }
        )

from apps.applications.constants.faculty_enums import FacultyTimelineEventType

class CollegeApplicationSelectAPIView(CollegeScopedAPIView):
    """API for selecting an interviewed candidate."""
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        app = _get_application(request.user, kwargs.get("application_id"))
        if not app:
            return JsonResponse({"success": False, "error": "Application not found."}, status=404)
        if app.status != FacultyApplicationStatus.INTERVIEW_COMPLETED:
            return _error_response("Application is not in interview completed state.")

        data = _parse_json(request)
        notes = data.get("notes", "").strip()

        try:
            with transaction.atomic():
                FacultyApplicationService().update_status_for_actor(
                    app,
                    FacultyApplicationStatus.SELECTED,
                    notes or "Candidate selected after interview.",
                    actor=request.user,
                )
            return JsonResponse({"status": "success", "message": "Candidate successfully selected."})
        except Exception as e:
            return _error_response(e)


class CollegeApplicationSetJoiningAPIView(CollegeScopedAPIView):
    """API for initiating the joining process."""
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        app = _get_application(request.user, kwargs.get("application_id"))
        if not app:
            return JsonResponse({"success": False, "error": "Application not found."}, status=404)
        valid_statuses = [FacultyApplicationStatus.SELECTED, FacultyApplicationStatus.OFFER_ACCEPTED]
        if app.status not in valid_statuses:
            return _error_response("Application must be selected or offer accepted to initiate joining.")

        data = _parse_json(request)
        joining_date = data.get("joining_date")
        if not joining_date:
            return _error_response("Joining date is required.")

        try:
            with transaction.atomic():
                FacultyApplicationService().update_status_for_actor(
                    app,
                    FacultyApplicationStatus.JOINING_IN_PROGRESS,
                    f"Candidate expected to join on {joining_date}.",
                    actor=request.user,
                )
            return JsonResponse({"status": "success", "message": "Joining initiated."})
        except Exception as e:
            return _error_response(e)


class CollegeApplicationConfirmJoinedAPIView(CollegeScopedAPIView):
    """API to confirm the candidate has actually joined."""
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        app = _get_application(request.user, kwargs.get("application_id"))
        if not app:
            return JsonResponse({"success": False, "error": "Application not found."}, status=404)
        
        valid_statuses = [
            FacultyApplicationStatus.SELECTED, 
            FacultyApplicationStatus.OFFER_ACCEPTED, 
            FacultyApplicationStatus.JOINING_IN_PROGRESS
        ]
        
        if app.status not in valid_statuses:
            return _error_response("Invalid current status for joining confirmation.")

        try:
            with transaction.atomic():
                FacultyApplicationService().update_status_for_actor(
                    app,
                    FacultyApplicationStatus.JOINED,
                    "Candidate has successfully joined the institution.",
                    actor=request.user,
                )
            return JsonResponse({"status": "success", "message": "Candidate joined successfully."})
        except Exception as e:
            return _error_response(e)


class CollegeApplicationReportExitAPIView(CollegeScopedAPIView):
    """API to report if a joined candidate leaves (for 90-day guarantee)."""
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        app = _get_application(request.user, kwargs.get("application_id"))
        if not app:
            return JsonResponse({"success": False, "error": "Application not found."}, status=404)
        if app.status != FacultyApplicationStatus.JOINED:
            return _error_response("Only joined candidates can be reported as exited.")

        data = _parse_json(request)
        reason = data.get("reason", "").strip()
        date_of_exit = data.get("date_of_exit")
        
        if not reason or not date_of_exit:
            return _error_response("Both reason and date of exit are required.")

        try:
            with transaction.atomic():
                # Here we could update status to Exited / Absconded / Terminated or just log the event.
                # Since we don't have an EXITED status in FacultyApplicationStatus, we might log it and create a GuaranteeClaim.
                # For now, let's just log it in the timeline.
                
                app.timeline.create(
                    actor=request.user,
                    title="Candidate Exited",
                    description=f"Candidate exited on {date_of_exit}. Reason: {reason}",
                    event_type=FacultyTimelineEventType.STATUS_CHANGED,
                )
                
            return JsonResponse({"status": "success", "message": "Candidate exit reported."})
        except Exception as e:
            return _error_response(e)
