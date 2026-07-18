from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.academic_recruitment.api.schema import vacancy_inbox_schema
from apps.academic_recruitment.selectors.profile_selector import (
    ProfessorProfileSelector,
)
from apps.applications.api.faculty_schema import (
    faculty_application_create_schema,
    faculty_application_detail_schema,
    faculty_application_history_schema,
    faculty_application_notes_schema,
    faculty_application_search_schema,
    faculty_application_statistics_schema,
    faculty_application_status_schema,
    faculty_application_timeline_schema,
    faculty_application_withdraw_schema,
    college_application_list_schema,
    institution_application_list_schema,
    professor_application_list_schema,
)
from apps.applications.api.v1.serializers import (
    FacultyApplicationCreateSerializer,
    FacultyApplicationNotesSerializer,
    FacultyApplicationSerializer,
    FacultyApplicationStatusHistorySerializer,
    FacultyApplicationStatusSerializer,
    FacultyApplicationTimelineSerializer,
)
from apps.applications.models import FacultyApplication
from apps.applications.permissions.application_permissions import (
    CanManageFacultyApplicationStatus,
    CanViewFacultyApplication,
)
from apps.applications.selectors.application_selector import (
    FacultyApplicationSearchSelector,
    FacultyApplicationSelector,
)
from apps.applications.services.application_authorization_service import (
    ApplicationAuthorizationService,
)
from apps.applications.services.application_document_service import (
    ApplicationDocumentService,
)
from apps.applications.services.faculty_application_service import (
    FacultyApplicationService,
)
from apps.applications.services.faculty_application_statistics_service import (
    FacultyApplicationStatisticsService,
)
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsProfessorUser
from apps.core.permissions.roles import IsCollegeUser
from apps.core.views.base import EnvelopeAPIView
from apps.faculty.selectors.vacancy_selector import (
    FacultyVacancySelector,
    PublicFacultyVacancySelector,
)


class FacultyApplicationListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfessorUser]
    throttle_classes = [ApplicationThrottle]

    @professor_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        professor = ProfessorProfileSelector().for_user(request.user)
        queryset = FacultyApplication.objects.none()
        if professor:
            queryset = FacultyApplicationSelector().for_professor(
                professor, status=request.query_params.get("status")
            )
        return paginate_envelope(request, queryset, FacultyApplicationSerializer)

    @faculty_application_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = FacultyApplicationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        professor = ProfessorProfileSelector().for_user(request.user)
        if not professor:
            return self.error_response(
                "PROFILE_REQUIRED", "Professor profile required.", status=400
            )
        vacancy = PublicFacultyVacancySelector().get_published(
            serializer.validated_data["vacancy_id"]
        )
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        cv_file = ApplicationDocumentService().resolve_cv_for_professor(
            professor=professor,
            user=request.user,
            cv_file_id=serializer.validated_data.get("cv_file_id"),
        )
        data = serializer.validated_data
        application = FacultyApplicationService().apply(
            vacancy=vacancy,
            professor=professor,
            cover_letter=data.get("cover_letter", ""),
            cv_file=cv_file,
            expected_salary=data.get("expected_salary"),
            current_institution=data.get("current_institution", ""),
            current_designation=data.get("current_designation", ""),
            source=data.get("source", ""),
        )
        return self.success_response(
            FacultyApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED,
        )


class CollegeFacultyApplicationSearchView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_search_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        queryset = FacultyApplicationSearchSelector().search(
            query=request.query_params.get("q", ""),
            status=request.query_params.get("status", ""),
            college_id=request.query_params.get("college_id"),
            vacancy_id=request.query_params.get("vacancy_id"),
            professor_id=request.query_params.get("professor_id"),
            department=request.query_params.get("department", ""),
            college_user=request.user,
            sort=request.query_params.get("sort", "recent"),
        )
        return paginate_envelope(request, queryset, FacultyApplicationSerializer)


class CollegeFacultyApplicationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    @college_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        queryset = FacultyApplicationSelector().for_college_user(
            request.user, status=request.query_params.get("status")
        )
        return paginate_envelope(request, queryset, FacultyApplicationSerializer)


class InstitutionFacultyApplicationListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    @institution_application_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        from apps.colleges.selectors.college_selector import CollegeMemberSelector

        if (
            not CollegeMemberSelector()
            .for_user(request.user)
            .filter(college_id=college_id)
            .exists()
        ):
            return self.error_response(
                "PERMISSION_DENIED",
                "You are not a member of this institution.",
                status=403,
            )
        queryset = FacultyApplicationSelector().for_college(
            college_id,
            status=request.query_params.get("status"),
            vacancy_id=request.query_params.get("vacancy_id"),
            department=request.query_params.get("department"),
        )
        return paginate_envelope(request, queryset, FacultyApplicationSerializer)


class FacultyApplicationStatisticsView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_statistics_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        college_id = request.query_params.get("college_id")
        if college_id:
            stats = FacultyApplicationStatisticsService().institution_dashboard(
                college_id=college_id, college_user=request.user
            )
        else:
            stats = FacultyApplicationStatisticsService().college_dashboard(
                request.user
            )
        return self.success_response(stats)


class VacancyApplicationInboxView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    @vacancy_inbox_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy = FacultyVacancySelector().filter_by(pk=vacancy_id).first()
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        ApplicationAuthorizationService().ensure_can_view_faculty_applications_for_vacancy(
            vacancy, request.user
        )
        queryset = FacultyApplicationSelector().for_vacancy(
            vacancy, status=request.query_params.get("status")
        )
        return paginate_envelope(request, queryset, FacultyApplicationSerializer)


class FacultyApplicationStatusView(EnvelopeAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        CanManageFacultyApplicationStatus,
    ]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_status_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        serializer = FacultyApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        application = FacultyApplicationService().update_status_for_actor(
            application,
            serializer.validated_data["status"],
            serializer.validated_data.get("notes", ""),
            actor=request.user,
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        return self.success_response(FacultyApplicationSerializer(application).data)


class FacultyApplicationWithdrawView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfessorUser]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_withdraw_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        application = FacultyApplicationService().withdraw(
            application, actor=request.user
        )
        return self.success_response(FacultyApplicationSerializer(application).data)


class FacultyApplicationNotesView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, CanViewFacultyApplication]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_notes_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        serializer = FacultyApplicationNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = FacultyApplicationService()
        if "college_notes" in data:
            application = service.add_college_notes(
                application, notes=data["college_notes"], actor=request.user
            )
        if "internal_remarks" in data:
            application = service.add_internal_remarks(
                application, remarks=data["internal_remarks"], actor=request.user
            )
        if "professor_notes" in data:
            application = service.add_professor_notes(
                application, notes=data["professor_notes"], actor=request.user
            )
        return self.success_response(FacultyApplicationSerializer(application).data)


class FacultyApplicationStatusHistoryView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_history_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_faculty_application(
            application, request.user
        )
        from apps.applications.selectors.status_history_selector import (
            FacultyApplicationStatusHistorySelector,
        )

        history = FacultyApplicationStatusHistorySelector().for_application(application)
        return self.success_response(
            FacultyApplicationStatusHistorySerializer(history, many=True).data
        )


class FacultyApplicationTimelineView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_timeline_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_faculty_application(
            application, request.user
        )
        from apps.applications.selectors.timeline_selector import (
            FacultyApplicationTimelineSelector,
        )

        timeline = FacultyApplicationTimelineSelector().for_application(application)
        return self.success_response(
            FacultyApplicationTimelineSerializer(timeline, many=True).data
        )


class FacultyApplicationDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @faculty_application_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        ApplicationAuthorizationService().ensure_can_view_faculty_application(
            application, request.user
        )
        return self.success_response(FacultyApplicationSerializer(application).data)

    @faculty_application_detail_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        FacultyApplicationService().soft_delete(application, actor=request.user)
        return self.success_response({"deleted": True})
