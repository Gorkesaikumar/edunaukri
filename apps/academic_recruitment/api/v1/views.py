from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle, ResumeUploadThrottle

from apps.accounts.profiles.api.v1.serializers import (
    CollegeProfileSerializer,
    ProfessorProfileSerializer,
)
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.permissions.profile_permissions import (
    CanManageOwnProfile,
    IsProfileOwner,
)
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.academic_recruitment.api.schema import (
    college_application_list_schema,
    college_vacancy_list_schema,
    faculty_application_create_schema,
    faculty_application_detail_schema,
    faculty_application_history_schema,
    faculty_application_status_schema,
    faculty_application_withdraw_schema,
    professor_application_list_schema,
    vacancy_close_schema,
    vacancy_create_schema,
    vacancy_detail_schema,
    vacancy_inbox_schema,
    vacancy_list_schema,
    vacancy_publish_schema,
    vacancy_update_schema,
)
from apps.academic_recruitment.api.v1.serializers import (
    FacultyVacancyCreateSerializer,
    FacultyVacancySerializer,
    FacultyVacancyUpdateSerializer,
)
from apps.academic_recruitment.selectors.profile_selector import (
    ProfessorProfileSelector,
)
from apps.applications.api.v1.serializers import (
    FacultyApplicationCreateSerializer,
    FacultyApplicationSerializer,
    FacultyApplicationStatusHistorySerializer,
    FacultyApplicationStatusSerializer,
)
from apps.applications.models import FacultyApplication
from apps.applications.selectors.application_selector import FacultyApplicationSelector
from apps.applications.selectors.status_history_selector import (
    FacultyApplicationStatusHistorySelector,
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
from apps.core.pagination import paginate_envelope
from apps.colleges.selectors.college_selector import (
    CollegeMemberSelector,
    CollegeSelector,
)
from apps.core.permissions.base import IsCollegeUser, IsProfessorUser
from apps.core.permissions.roles import IsCollege
from apps.core.views.base import EnvelopeAPIView
from apps.faculty.models import FacultyVacancy
from apps.faculty.selectors.vacancy_selector import (
    FacultyVacancySelector,
    PublicFacultyVacancySelector,
)
from apps.faculty.services.vacancy_service import VacancyPostingService


class ProfessorProfileView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfessorUser]
    throttle_classes = [ResumeUploadThrottle]

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                permissions.IsAuthenticated(),
                IsProfessorUser(),
                CanManageOwnProfile(),
            ]
        if self.request.method == "PATCH":
            return [permissions.IsAuthenticated(), IsProfessorUser(), IsProfileOwner()]
        return super().get_permissions()

    @extend_schema(responses={200: dict})
    def get(self, request):
        profile = ProfessorProfileSelector().for_user(request.user)
        if not profile:
            return self.success_response(None)
        return self.success_response(ProfessorProfileSerializer(profile).data)

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        profile = ProfileService().create_profile(
            user=request.user, profile_type=ProfileType.PROFESSOR, data=request.data
        )
        return self.success_response(
            ProfessorProfileSerializer(profile).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=None, responses={200: dict})
    def patch(self, request):
        profile = ProfileService().update_profile(
            user=request.user, profile_type=ProfileType.PROFESSOR, data=request.data
        )
        return self.success_response(ProfessorProfileSerializer(profile).data)


class CollegeListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollege]
    throttle_classes = [ResumeUploadThrottle]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsCollege(), CanManageOwnProfile()]
        if self.request.method == "PATCH":
            return [permissions.IsAuthenticated(), IsCollege(), IsProfileOwner()]
        return super().get_permissions()

    @extend_schema(responses={200: dict})
    def get(self, request):
        membership = CollegeMemberSelector().primary_for_user(request.user)
        if not membership:
            return self.success_response(None)
        return self.success_response(CollegeProfileSerializer(membership.college).data)

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        college = ProfileService().create_profile(
            user=request.user, profile_type=ProfileType.COLLEGE, data=request.data
        )
        return self.success_response(
            CollegeProfileSerializer(college).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=None, responses={200: dict})
    def patch(self, request):
        college = ProfileService().update_profile(
            user=request.user, profile_type=ProfileType.COLLEGE, data=request.data
        )
        return self.success_response(CollegeProfileSerializer(college).data)


class VacancyListCreateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @vacancy_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().published(
            search=request.query_params.get("search")
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)

    @vacancy_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = FacultyVacancyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        college = CollegeSelector().get_or_none(serializer.validated_data["college_id"])
        if not college:
            return self.error_response("NOT_FOUND", "College not found.", status=404)
        vacancy = VacancyPostingService().create_draft(
            college=college, college_user=request.user, data=serializer.validated_data
        )
        return self.success_response(
            FacultyVacancySerializer(vacancy).data, status=status.HTTP_201_CREATED
        )


class CollegeVacancyListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollege]
    throttle_classes = [ApplicationThrottle]

    @college_vacancy_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().for_college_user(request.user)
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class VacancyDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ApplicationThrottle]

    @vacancy_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy = FacultyVacancySelector().filter_by(pk=vacancy_id).first()
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        if vacancy.status != FacultyVacancy.VacancyStatus.PUBLISHED:
            if (
                not CollegeMemberSelector()
                .for_user(request.user)
                .filter(college_id=vacancy.college_id)
                .exists()
            ):
                return self.error_response(
                    "NOT_FOUND", "Vacancy not found.", status=404
                )
        return self.success_response(FacultyVacancySerializer(vacancy).data)

    @vacancy_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, vacancy_id):
        vacancy = FacultyVacancySelector().filter_by(pk=vacancy_id).first()
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        serializer = FacultyVacancyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vacancy = VacancyPostingService().update_draft(
            vacancy, college_user=request.user, data=serializer.validated_data
        )
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class VacancyPublishView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollege]
    throttle_classes = [ApplicationThrottle]

    @vacancy_publish_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        vacancy = FacultyVacancySelector().filter_by(pk=vacancy_id).first()
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        vacancy = VacancyPostingService().publish(vacancy, college_user=request.user)
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class VacancyCloseView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollege]
    throttle_classes = [ApplicationThrottle]

    @vacancy_close_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        vacancy = FacultyVacancySelector().filter_by(pk=vacancy_id).first()
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        vacancy = VacancyPostingService().close(vacancy, college_user=request.user)
        return self.success_response(FacultyVacancySerializer(vacancy).data)


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
    permission_classes = [permissions.IsAuthenticated]
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
        history = FacultyApplicationStatusHistorySelector().for_application(application)
        return self.success_response(
            FacultyApplicationStatusHistorySerializer(history, many=True).data
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
