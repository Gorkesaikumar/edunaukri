from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle, BruteForceIPThrottle

from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsCollegeUser
from apps.core.views.base import EnvelopeAPIView
from apps.faculty.api.schema import (
    vacancy_archive_schema,
    vacancy_close_schema,
    vacancy_college_list_schema,
    vacancy_create_schema,
    vacancy_dashboard_schema,
    vacancy_delete_schema,
    vacancy_detail_schema,
    vacancy_duplicate_schema,
    vacancy_list_create_list_schema,
    vacancy_mine_list_schema,
    vacancy_pause_schema,
    vacancy_preview_schema,
    vacancy_public_detail_schema,
    vacancy_public_list_schema,
    vacancy_publish_schema,
    vacancy_reopen_schema,
    vacancy_statistics_schema,
    vacancy_template_list_schema,
    vacancy_unpublish_schema,
    vacancy_update_schema,
    vacancy_visibility_schema,
)
from apps.faculty.api.v1.serializers import (
    FacultyVacancyCreateSerializer,
    FacultyVacancySerializer,
    FacultyVacancyUpdateSerializer,
    VacancyVisibilitySerializer,
)
from apps.faculty.permissions.vacancy_permissions import CanManageVacancy
from apps.faculty.repositories.vacancy_repository import FacultyVacancyRepository
from apps.faculty.selectors.vacancy_search import VacancySearchSelector
from apps.faculty.selectors.vacancy_selector import (
    CollegeVacancySelector,
    FacultyVacancySelector,
    PublicFacultyVacancySelector,
)
from apps.faculty.services.faculty_vacancy_service import FacultyVacancyService
from apps.faculty.services.vacancy_lifecycle_service import FacultyLifecycleService
from apps.faculty.services.vacancy_publication_service import FacultyPublicationService
from apps.faculty.services.vacancy_statistics_service import FacultyStatisticsService
from apps.faculty.services.vacancy_visibility_service import FacultyVisibilityService


class _CollegeVacancyView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    def _vacancy_or_error(self, vacancy_id):
        vacancy = FacultyVacancySelector().get_or_none(vacancy_id)
        if not vacancy:
            return None, self.error_response(
                "NOT_FOUND", "Vacancy not found.", status=404
            )
        return vacancy, None


class VacancyListCreateView(_CollegeVacancyView):
    @vacancy_list_create_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().for_college_user(
            request.user, status=request.query_params.get("status")
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)

    @vacancy_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = FacultyVacancyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vacancy = FacultyVacancyService().create_vacancy(
            college_user=request.user, data=serializer.validated_data
        )
        return self.success_response(
            FacultyVacancySerializer(vacancy).data, status=status.HTTP_201_CREATED
        )


class CollegeUserVacancyListView(_CollegeVacancyView):
    @vacancy_mine_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().for_college_user(
            request.user, status=request.query_params.get("status")
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class VacancyTemplateListView(_CollegeVacancyView):
    @vacancy_template_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().templates(request.user)
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class VacancyDashboardView(_CollegeVacancyView):
    @vacancy_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(
            FacultyStatisticsService().college_user_dashboard(request.user)
        )


class VacancyDetailView(_CollegeVacancyView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser, CanManageVacancy]

    @vacancy_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        return self.success_response(FacultyVacancySerializer(vacancy).data)

    @vacancy_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        serializer = FacultyVacancyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vacancy = FacultyVacancyService().update_vacancy(
            vacancy=vacancy, college_user=request.user, data=serializer.validated_data
        )
        return self.success_response(FacultyVacancySerializer(vacancy).data)

    @vacancy_delete_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        FacultyVacancyService().soft_delete(vacancy=vacancy, college_user=request.user)
        return self.success_response({"deleted": True})


class VacancyPreviewView(_CollegeVacancyView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser, CanManageVacancy]

    @vacancy_preview_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class _VacancyActionView(_CollegeVacancyView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser, CanManageVacancy]

    def _run(self, request, vacancy_id, handler):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        vacancy = handler(request.user, vacancy)
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class VacancyPublishView(_VacancyActionView):
    @vacancy_publish_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        return self._run(
            request,
            vacancy_id,
            lambda u, v: FacultyPublicationService().publish(vacancy=v, college_user=u),
        )


class VacancyUnpublishView(_VacancyActionView):
    @vacancy_unpublish_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        return self._run(
            request,
            vacancy_id,
            lambda u, v: FacultyPublicationService().unpublish(
                vacancy=v, college_user=u
            ),
        )


class VacancyPauseView(_VacancyActionView):
    @vacancy_pause_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        return self._run(
            request,
            vacancy_id,
            lambda u, v: FacultyLifecycleService().pause(vacancy=v, college_user=u),
        )


class VacancyReopenView(_VacancyActionView):
    @vacancy_reopen_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        return self._run(
            request,
            vacancy_id,
            lambda u, v: FacultyLifecycleService().reopen(vacancy=v, college_user=u),
        )


class VacancyCloseView(_VacancyActionView):
    @vacancy_close_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        return self._run(
            request,
            vacancy_id,
            lambda u, v: FacultyLifecycleService().close(vacancy=v, college_user=u),
        )


class VacancyArchiveView(_VacancyActionView):
    @vacancy_archive_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        return self._run(
            request,
            vacancy_id,
            lambda u, v: FacultyLifecycleService().archive(vacancy=v, college_user=u),
        )


class VacancyDuplicateView(_VacancyActionView):
    @vacancy_duplicate_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        clone = FacultyVacancyService().duplicate_vacancy(
            vacancy=vacancy, college_user=request.user
        )
        return self.success_response(
            FacultyVacancySerializer(clone).data, status=status.HTTP_201_CREATED
        )


class VacancyVisibilityView(_VacancyActionView):
    @vacancy_visibility_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        serializer = VacancyVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        service = FacultyVisibilityService()
        if "is_featured" in data:
            vacancy = service.set_featured(
                vacancy=vacancy, college_user=request.user, value=data["is_featured"]
            )
        if "is_urgent" in data:
            vacancy = service.set_urgent(
                vacancy=vacancy, college_user=request.user, value=data["is_urgent"]
            )
        if "visibility" in data:
            vacancy = service.set_visibility(
                vacancy=vacancy,
                college_user=request.user,
                visibility=data["visibility"],
            )
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class VacancyStatisticsView(_CollegeVacancyView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser, CanManageVacancy]

    @vacancy_statistics_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        stats = FacultyStatisticsService().vacancy_statistics(
            vacancy=vacancy, college_user=request.user
        )
        return self.success_response(stats)


class CollegeVacancyListView(_CollegeVacancyView):
    @vacancy_college_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        from apps.colleges.selectors.college_selector import CollegeMemberSelector

        if not CollegeMemberSelector().is_member(request.user, college_id):
            return self.error_response(
                "PERMISSION_DENIED",
                "You are not a member of this institution.",
                status=403,
            )
        vacancies = CollegeVacancySelector().for_college(
            college_id, status=request.query_params.get("status")
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class PublicVacancyListView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def _as_int(value):
        try:
            return int(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    @vacancy_public_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        params = request.query_params
        vacancies = VacancySearchSelector().search(
            query=params.get("q", ""),
            department=params.get("department", ""),
            qualification=params.get("qualification", ""),
            designation=params.get("designation", ""),
            specialization=params.get("specialization", ""),
            location=params.get("location", ""),
            employment_type=params.get("employment_type", ""),
            work_type=params.get("work_type", ""),
            experience=self._as_int(params.get("experience")),
            salary_min=params.get("salary_min") or None,
            salary_max=params.get("salary_max") or None,
            sort=params.get("sort", "recent"),
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class PublicVacancyDetailView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]

    @vacancy_public_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy = PublicFacultyVacancySelector().get_published(vacancy_id)
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        FacultyVacancyRepository().increment_view_count(vacancy)
        vacancy.refresh_from_db(fields=["view_count"])
        return self.success_response(FacultyVacancySerializer(vacancy).data)
