from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.faculty.api.schema import (
    admin_vacancy_dashboard_schema,
    admin_vacancy_detail_schema,
    admin_vacancy_list_schema,
    admin_vacancy_reject_schema,
)
from apps.faculty.api.v1.serializers import (
    FacultyVacancySerializer,
    VacancyModerationSerializer,
)
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.faculty.services.vacancy_publication_service import FacultyPublicationService
from apps.faculty.services.vacancy_statistics_service import FacultyStatisticsService


class _AdminVacancyView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    def _vacancy_or_error(self, vacancy_id):
        vacancy = FacultyVacancySelector().get_or_none(vacancy_id)
        if not vacancy:
            return None, self.error_response(
                "NOT_FOUND", "Vacancy not found.", status=404
            )
        return vacancy, None


class AdminVacancyListView(_AdminVacancyView):
    @admin_vacancy_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().admin_list(
            status=request.query_params.get("status"),
            college_id=request.query_params.get("college_id"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class AdminVacancyDetailView(_AdminVacancyView):
    @admin_vacancy_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class AdminVacancyRejectView(_AdminVacancyView):
    @admin_vacancy_reject_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id):
        vacancy, error = self._vacancy_or_error(vacancy_id)
        if error:
            return error
        serializer = VacancyModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vacancy = FacultyPublicationService().admin_reject(
            vacancy=vacancy,
            admin_id=request.user.pk,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class AdminVacancyDashboardView(_AdminVacancyView):
    @admin_vacancy_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(FacultyStatisticsService().platform_dashboard())
