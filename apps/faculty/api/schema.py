from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.faculty.api.v1.serializers import (
    FacultyVacancyCreateSerializer,
    FacultyVacancyUpdateSerializer,
    VacancyModerationSerializer,
    VacancyVisibilitySerializer,
)

TAG = "faculty-vacancies"
ADMIN_TAG = "admin-faculty-vacancies"

Envelope = inline_serializer(
    name="FacultyVacancyEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

_SEARCH_PARAMS = [
    OpenApiParameter(name="q", type=str, required=False, description="Keyword search"),
    OpenApiParameter(name="department", type=str, required=False),
    OpenApiParameter(name="qualification", type=str, required=False),
    OpenApiParameter(name="designation", type=str, required=False),
    OpenApiParameter(name="specialization", type=str, required=False),
    OpenApiParameter(name="location", type=str, required=False),
    OpenApiParameter(name="employment_type", type=str, required=False),
    OpenApiParameter(name="work_type", type=str, required=False),
    OpenApiParameter(name="experience", type=int, required=False),
    OpenApiParameter(name="salary_min", type=float, required=False),
    OpenApiParameter(name="salary_max", type=float, required=False),
    OpenApiParameter(
        name="sort",
        type=str,
        required=False,
        description="recent|oldest|salary_high|salary_low|title",
    ),
]

vacancy_list_create_list_schema = extend_schema(
    tags=[TAG], summary="List the college user's vacancies", responses={200: Envelope}
)
vacancy_create_schema = extend_schema(
    tags=[TAG],
    summary="Create a vacancy",
    request=FacultyVacancyCreateSerializer,
    responses={201: Envelope},
)
vacancy_detail_schema = extend_schema(
    tags=[TAG], summary="Retrieve a vacancy", responses={200: Envelope}
)
vacancy_update_schema = extend_schema(
    tags=[TAG],
    summary="Update a vacancy",
    request=FacultyVacancyUpdateSerializer,
    responses={200: Envelope},
)
vacancy_delete_schema = extend_schema(
    tags=[TAG], summary="Soft delete a vacancy", responses={200: Envelope}
)
vacancy_preview_schema = extend_schema(
    tags=[TAG], summary="Preview a vacancy (owner view)", responses={200: Envelope}
)
vacancy_mine_list_schema = extend_schema(
    tags=[TAG],
    summary="List vacancies owned by the college user",
    responses={200: Envelope},
)
vacancy_template_list_schema = extend_schema(
    tags=[TAG],
    summary="List the college user's vacancy templates",
    responses={200: Envelope},
)
vacancy_college_list_schema = extend_schema(
    tags=[TAG], summary="List a college's vacancies", responses={200: Envelope}
)
vacancy_public_list_schema = extend_schema(
    tags=[TAG],
    summary="Search public / published faculty vacancies",
    parameters=_SEARCH_PARAMS,
    responses={200: Envelope},
)
vacancy_public_detail_schema = extend_schema(
    tags=[TAG],
    summary="Retrieve a published vacancy (public)",
    responses={200: Envelope},
)
vacancy_publish_schema = extend_schema(
    tags=[TAG], summary="Publish a vacancy", responses={200: Envelope}
)
vacancy_unpublish_schema = extend_schema(
    tags=[TAG], summary="Unpublish a vacancy", responses={200: Envelope}
)
vacancy_pause_schema = extend_schema(
    tags=[TAG], summary="Pause a published vacancy", responses={200: Envelope}
)
vacancy_reopen_schema = extend_schema(
    tags=[TAG], summary="Reopen a paused/closed vacancy", responses={200: Envelope}
)
vacancy_close_schema = extend_schema(
    tags=[TAG], summary="Close a vacancy", responses={200: Envelope}
)
vacancy_archive_schema = extend_schema(
    tags=[TAG], summary="Archive a vacancy", responses={200: Envelope}
)
vacancy_duplicate_schema = extend_schema(
    tags=[TAG], summary="Duplicate / clone a vacancy", responses={201: Envelope}
)
vacancy_visibility_schema = extend_schema(
    tags=[TAG],
    summary="Update featured/urgent/visibility flags",
    request=VacancyVisibilitySerializer,
    responses={200: Envelope},
)
vacancy_statistics_schema = extend_schema(
    tags=[TAG], summary="Vacancy statistics", responses={200: Envelope}
)
vacancy_dashboard_schema = extend_schema(
    tags=[TAG],
    summary="College-user vacancy dashboard summary",
    responses={200: Envelope},
)

admin_vacancy_list_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: list all faculty vacancies",
    parameters=[
        OpenApiParameter(name="status", type=str, required=False),
        OpenApiParameter(name="college_id", type=str, required=False),
        OpenApiParameter(name="search", type=str, required=False),
    ],
    responses={200: Envelope},
)
admin_vacancy_detail_schema = extend_schema(
    tags=[ADMIN_TAG], summary="Admin: retrieve a vacancy", responses={200: Envelope}
)
admin_vacancy_reject_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: reject a vacancy",
    request=VacancyModerationSerializer,
    responses={200: Envelope},
)
admin_vacancy_dashboard_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: platform-wide vacancy dashboard summary",
    responses={200: Envelope},
)
