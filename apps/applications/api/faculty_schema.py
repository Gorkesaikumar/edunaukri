from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.applications.api.v1.serializers import (
    FacultyApplicationCreateSerializer,
    FacultyApplicationNotesSerializer,
    FacultyApplicationStatusSerializer,
)

Envelope = inline_serializer(
    name="FacultyApplicationEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

_SEARCH_PARAMS = [
    OpenApiParameter(name="q", type=str, required=False),
    OpenApiParameter(name="status", type=str, required=False),
    OpenApiParameter(name="college_id", type=str, required=False),
    OpenApiParameter(name="vacancy_id", type=str, required=False),
    OpenApiParameter(name="professor_id", type=str, required=False),
    OpenApiParameter(name="department", type=str, required=False),
    OpenApiParameter(
        name="sort", type=str, required=False, description="recent|oldest|status"
    ),
]

professor_application_list_schema = extend_schema(
    tags=["faculty-applications"],
    summary="List own faculty applications",
    parameters=[OpenApiParameter(name="status", type=str, required=False)],
    responses={200: Envelope},
)

faculty_application_create_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Apply to a published faculty vacancy",
    request=FacultyApplicationCreateSerializer,
    responses={201: Envelope},
)

college_application_list_schema = extend_schema(
    tags=["faculty-applications"],
    summary="List applications for college user's institutions",
    parameters=[OpenApiParameter(name="status", type=str, required=False)],
    responses={200: Envelope},
)

faculty_application_search_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Search faculty applications for college users",
    parameters=_SEARCH_PARAMS,
    responses={200: Envelope},
)

institution_application_list_schema = extend_schema(
    tags=["faculty-applications"],
    summary="List applications for a specific institution",
    parameters=[
        OpenApiParameter(name="status", type=str, required=False),
        OpenApiParameter(name="vacancy_id", type=str, required=False),
        OpenApiParameter(name="department", type=str, required=False),
    ],
    responses={200: Envelope},
)

faculty_application_statistics_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Faculty application statistics for college or institution",
    parameters=[OpenApiParameter(name="college_id", type=str, required=False)],
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

faculty_application_notes_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Update college/professor notes",
    request=FacultyApplicationNotesSerializer,
    responses={200: Envelope},
)

faculty_application_history_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Faculty application status history",
    responses={200: Envelope},
)

faculty_application_timeline_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Faculty application timeline",
    responses={200: Envelope},
)

faculty_application_detail_schema = extend_schema(
    tags=["faculty-applications"],
    summary="Faculty application detail",
    responses={200: Envelope},
)
