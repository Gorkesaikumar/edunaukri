from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.academic_recruitment.api.v1.profile_serializers import CollegeSerializer
from apps.academic_recruitment.api.v1.serializers import FacultyVacancySerializer
from apps.colleges.selectors.college_selector import CollegeSelector
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsPlatformAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

AdminEnvelope = inline_serializer(
    name="AdminVacancyEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

admin_vacancy_list_schema = extend_schema(
    tags=["admin-recruitment"],
    summary="Admin: list all faculty vacancies",
    responses={200: AdminEnvelope},
)

admin_college_list_schema = extend_schema(
    tags=["admin-recruitment"],
    summary="Admin: list all colleges",
    responses={200: AdminEnvelope},
)


class AdminCollegeListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @admin_college_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        colleges = CollegeSelector().admin_list(
            search=request.query_params.get("search")
        )
        return paginate_envelope(request, colleges, CollegeSerializer)


class AdminVacancyListView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [ApplicationThrottle]

    @admin_vacancy_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().admin_list(
            status=request.query_params.get("status"),
            college_id=request.query_params.get("college_id"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)
