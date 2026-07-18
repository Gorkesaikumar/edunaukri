from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.academic_recruitment.api.v1.serializers import (
    FacultyVacancyCreateSerializer,
    FacultyVacancySerializer,
    FacultyVacancyUpdateSerializer,
)
from apps.applications.api.v1.serializers import (
    FacultyApplicationCreateSerializer,
    FacultyApplicationSerializer,
    FacultyApplicationStatusSerializer,
)

Envelope = inline_serializer(
    name="FacultyRecruitmentEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

vacancy_list_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="List published faculty vacancies",
    parameters=[OpenApiParameter(name="search", type=str, required=False)],
    responses={200: Envelope},
)

vacancy_create_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="Create draft faculty vacancy",
    request=FacultyVacancyCreateSerializer,
    responses={201: Envelope},
)

college_vacancy_list_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="List college vacancies",
    responses={200: Envelope},
)

vacancy_detail_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="Get vacancy detail",
    responses={200: Envelope},
)

vacancy_update_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="Update draft vacancy",
    request=FacultyVacancyUpdateSerializer,
    responses={200: Envelope},
)

vacancy_publish_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="Publish draft vacancy",
    responses={200: Envelope},
)

vacancy_close_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="Close vacancy",
    responses={200: Envelope},
)

vacancy_inbox_schema = extend_schema(
    tags=["faculty-recruitment"],
    summary="List applications for a vacancy",
    responses={200: Envelope},
)

professor_application_list_schema = extend_schema(
    tags=["faculty-applications"],
    summary="List own faculty applications",
    responses={200: Envelope},
)

faculty_application_create_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Apply to a published vacancy",
    request=FacultyApplicationCreateSerializer,
    responses={201: Envelope},
)

college_application_list_schema = extend_schema(
    tags=["faculty-applications"],
    summary="List applications for college vacancies",
    responses={200: Envelope},
)

faculty_application_status_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Update faculty application status",
    request=FacultyApplicationStatusSerializer,
    responses={200: Envelope},
)

faculty_application_withdraw_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Withdraw own faculty application",
    responses={200: Envelope},
)

faculty_application_history_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Get faculty application status history",
    responses={200: Envelope},
)

faculty_application_detail_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Get faculty application detail",
    responses={200: Envelope},
)
