from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.applications.api.v1.serializers import (
    JobApplicationCreateSerializer,
    JobApplicationNotesSerializer,
    JobApplicationStatusSerializer,
)

Envelope = inline_serializer(
    name="ITApplicationEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

_SEARCH_PARAMS = [
    OpenApiParameter(name="q", type=str, required=False),
    OpenApiParameter(name="status", type=str, required=False),
    OpenApiParameter(name="company_id", type=str, required=False),
    OpenApiParameter(name="job_posting_id", type=str, required=False),
    OpenApiParameter(
        name="sort", type=str, required=False, description="recent|oldest|status"
    ),
]

seeker_application_list_schema = extend_schema(
    tags=["it-applications"],
    summary="List own job applications",
    parameters=[OpenApiParameter(name="status", type=str, required=False)],
    responses={200: Envelope},
)

application_create_schema = extend_schema(
    tags=["it-applications"],
    summary="Apply to a published job",
    request=JobApplicationCreateSerializer,
    responses={201: Envelope},
)

recruiter_application_list_schema = extend_schema(
    tags=["it-applications"],
    summary="Search applications for recruiter companies",
    parameters=_SEARCH_PARAMS,
    responses={200: Envelope},
)

company_application_list_schema = extend_schema(
    tags=["it-applications"],
    summary="List applications for a company",
    parameters=[
        OpenApiParameter(name="status", type=str, required=False),
        OpenApiParameter(name="job_posting_id", type=str, required=False),
    ],
    responses={200: Envelope},
)

application_search_schema = recruiter_application_list_schema

application_statistics_schema = extend_schema(
    tags=["it-applications"],
    summary="Application statistics for recruiter or company",
    parameters=[OpenApiParameter(name="company_id", type=str, required=False)],
    responses={200: Envelope},
)

application_status_schema = extend_schema(
    tags=["it-applications"],
    summary="Update application status",
    request=JobApplicationStatusSerializer,
    responses={200: Envelope},
)

application_withdraw_schema = extend_schema(
    tags=["it-applications"],
    summary="Withdraw own application",
    responses={200: Envelope},
)

application_notes_schema = extend_schema(
    tags=["it-applications"],
    summary="Update recruiter/candidate notes",
    request=JobApplicationNotesSerializer,
    responses={200: Envelope},
)

application_history_schema = extend_schema(
    tags=["it-applications"],
    summary="Get application status history",
    responses={200: Envelope},
)

application_timeline_schema = extend_schema(
    tags=["it-applications"],
    summary="Get full application timeline",
    responses={200: Envelope},
)

application_detail_schema = extend_schema(
    tags=["it-applications"],
    summary="Get or soft-delete application detail",
    responses={200: Envelope},
)

application_certificates_schema = extend_schema(
    tags=["it-applications"],
    summary="List candidate certificates for an application",
    responses={200: Envelope},
)
