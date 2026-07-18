from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.jobs.api.v1.serializers import (
    JobCreateSerializer,
    JobModerationSerializer,
    JobUpdateSerializer,
    JobVisibilitySerializer,
)

TAG = "jobs"
ADMIN_TAG = "admin-jobs"

Envelope = inline_serializer(
    name="JobEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

_SEARCH_PARAMS = [
    OpenApiParameter(name="q", type=str, required=False, description="Keyword search"),
    OpenApiParameter(name="location", type=str, required=False),
    OpenApiParameter(name="employment_type", type=str, required=False),
    OpenApiParameter(name="work_mode", type=str, required=False),
    OpenApiParameter(name="is_remote", type=bool, required=False),
    OpenApiParameter(
        name="skills",
        type=str,
        required=False,
        description="Comma-separated skill names",
    ),
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

job_list_create_list_schema = extend_schema(
    tags=[TAG], summary="List the recruiter's jobs", responses={200: Envelope}
)
job_create_schema = extend_schema(
    tags=[TAG],
    summary="Create a job",
    request=JobCreateSerializer,
    responses={201: Envelope},
)
job_detail_schema = extend_schema(
    tags=[TAG], summary="Retrieve a job", responses={200: Envelope}
)
job_update_schema = extend_schema(
    tags=[TAG],
    summary="Update a job",
    request=JobUpdateSerializer,
    responses={200: Envelope},
)
job_delete_schema = extend_schema(
    tags=[TAG], summary="Soft delete a job", responses={200: Envelope}
)
job_preview_schema = extend_schema(
    tags=[TAG], summary="Preview a job (owner view)", responses={200: Envelope}
)
job_recruiter_list_schema = extend_schema(
    tags=[TAG], summary="List jobs owned by the recruiter", responses={200: Envelope}
)
job_template_list_schema = extend_schema(
    tags=[TAG], summary="List the recruiter's job templates", responses={200: Envelope}
)
job_company_list_schema = extend_schema(
    tags=[TAG], summary="List a company's jobs", responses={200: Envelope}
)
job_public_list_schema = extend_schema(
    tags=[TAG],
    summary="Search public / published jobs",
    parameters=_SEARCH_PARAMS,
    responses={200: Envelope},
)
job_public_detail_schema = extend_schema(
    tags=[TAG], summary="Retrieve a published job (public)", responses={200: Envelope}
)
job_publish_schema = extend_schema(
    tags=[TAG], summary="Publish a job", request=None, responses={200: Envelope}
)
job_unpublish_schema = extend_schema(
    tags=[TAG], summary="Unpublish a job", request=None, responses={200: Envelope}
)
job_pause_schema = extend_schema(
    tags=[TAG], summary="Pause a published job", request=None, responses={200: Envelope}
)
job_reopen_schema = extend_schema(
    tags=[TAG], summary="Reopen a paused/closed job", request=None, responses={200: Envelope}
)
job_close_schema = extend_schema(
    tags=[TAG], summary="Close a job", request=None, responses={200: Envelope}
)
job_archive_schema = extend_schema(
    tags=[TAG], summary="Archive a job", request=None, responses={200: Envelope}
)
job_duplicate_schema = extend_schema(
    tags=[TAG], summary="Duplicate / clone a job", request=None, responses={201: Envelope}
)
job_visibility_schema = extend_schema(
    tags=[TAG],
    summary="Update featured/urgent/visibility flags",
    request=JobVisibilitySerializer,
    responses={200: Envelope},
)
job_statistics_schema = extend_schema(
    tags=[TAG], summary="Job statistics", responses={200: Envelope}
)
job_dashboard_schema = extend_schema(
    tags=[TAG], summary="Recruiter job dashboard summary", responses={200: Envelope}
)

admin_job_list_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: list all jobs",
    parameters=[
        OpenApiParameter(name="status", type=str, required=False),
        OpenApiParameter(name="company_id", type=str, required=False),
        OpenApiParameter(name="search", type=str, required=False),
    ],
    responses={200: Envelope},
)
admin_job_detail_schema = extend_schema(
    tags=[ADMIN_TAG], summary="Admin: retrieve a job", responses={200: Envelope}
)
admin_job_reject_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: reject a job",
    request=JobModerationSerializer,
    responses={200: Envelope},
)
admin_job_dashboard_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: platform-wide job dashboard summary",
    responses={200: Envelope},
)
