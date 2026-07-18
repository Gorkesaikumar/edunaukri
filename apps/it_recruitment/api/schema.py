from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.it_recruitment.api.v1.serializers import (
    CompanySerializer,
    CompanyUpdateSerializer,
    JobPostingCreateSerializer,
    JobPostingSerializer,
    JobPostingUpdateSerializer,
)

Envelope = inline_serializer(
    name="ITRecruitmentEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)

company_list_schema = extend_schema(
    tags=["it-recruitment"],
    summary="List recruiter companies",
    responses={200: Envelope},
)

company_create_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Create company",
    request=CompanySerializer,
    responses={201: Envelope},
)

company_detail_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Get company detail",
    responses={200: Envelope},
)

company_update_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Update company",
    request=CompanyUpdateSerializer,
    responses={200: Envelope},
)

job_list_schema = extend_schema(
    tags=["it-recruitment"],
    summary="List published jobs",
    parameters=[OpenApiParameter(name="search", type=str, required=False)],
    responses={200: Envelope},
)

job_create_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Create draft job posting",
    request=JobPostingCreateSerializer,
    responses={201: Envelope},
)

recruiter_job_list_schema = extend_schema(
    tags=["it-recruitment"],
    summary="List recruiter job postings",
    responses={200: Envelope},
)

job_detail_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Get job posting detail",
    responses={200: Envelope},
)

job_update_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Update draft job posting",
    request=JobPostingUpdateSerializer,
    responses={200: Envelope},
)

job_publish_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Publish draft job posting",
    request=None,
    responses={200: Envelope},
)

job_close_schema = extend_schema(
    tags=["it-recruitment"],
    summary="Close job posting",
    request=None,
    responses={200: Envelope},
)

job_inbox_schema = extend_schema(
    tags=["it-recruitment"],
    summary="List applications for a job posting",
    responses={200: Envelope},
)
