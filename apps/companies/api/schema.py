from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.companies.api.v1.serializers import (
    CompanyBrandingSerializer,
    CompanyCreateSerializer,
    CompanyLocationWriteSerializer,
    CompanyMemberAddSerializer,
    CompanyUpdateSerializer,
    CompanyVerificationSerializer,
)

TAG = "companies"
ADMIN_TAG = "admin-companies"

Envelope = inline_serializer(
    name="CompanyEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)


company_list_schema = extend_schema(
    tags=[TAG],
    summary="List companies for the authenticated recruiter",
    parameters=[OpenApiParameter(name="search", type=str, required=False)],
    responses={200: Envelope},
)

company_create_schema = extend_schema(
    tags=[TAG],
    summary="Create a company",
    request=CompanyCreateSerializer,
    responses={201: Envelope},
)

company_detail_schema = extend_schema(
    tags=[TAG],
    summary="Retrieve a company",
    responses={200: Envelope},
)

company_update_schema = extend_schema(
    tags=[TAG],
    summary="Update a company",
    request=CompanyUpdateSerializer,
    responses={200: Envelope},
)

company_delete_schema = extend_schema(
    tags=[TAG],
    summary="Soft delete a company (owner only)",
    responses={200: Envelope},
)

company_activate_schema = extend_schema(
    tags=[TAG],
    summary="Activate a company",
    responses={200: Envelope},
)

company_deactivate_schema = extend_schema(
    tags=[TAG],
    summary="Deactivate a company",
    responses={200: Envelope},
)

company_branding_schema = extend_schema(
    tags=[TAG],
    summary="Update company logo and/or cover banner",
    request=CompanyBrandingSerializer,
    responses={200: Envelope},
)

company_dashboard_schema = extend_schema(
    tags=[TAG],
    summary="Company dashboard summary for the recruiter",
    responses={200: Envelope},
)


company_location_list_schema = extend_schema(
    tags=[TAG],
    summary="List company locations",
    responses={200: Envelope},
)

company_location_create_schema = extend_schema(
    tags=[TAG],
    summary="Add a company location",
    request=CompanyLocationWriteSerializer,
    responses={201: Envelope},
)

company_location_detail_schema = extend_schema(
    tags=[TAG],
    summary="Update or delete a company location",
    request=CompanyLocationWriteSerializer,
    responses={200: Envelope},
)

company_member_list_schema = extend_schema(
    tags=[TAG],
    summary="List company members (recruiters)",
    responses={200: Envelope},
)

company_member_add_schema = extend_schema(
    tags=[TAG],
    summary="Add a recruiter to the company (owner only)",
    request=CompanyMemberAddSerializer,
    responses={201: Envelope},
)

company_member_remove_schema = extend_schema(
    tags=[TAG],
    summary="Remove a recruiter from the company (owner only)",
    responses={200: Envelope},
)


admin_company_list_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: list all companies",
    parameters=[
        OpenApiParameter(name="status", type=str, required=False),
        OpenApiParameter(name="is_active", type=bool, required=False),
        OpenApiParameter(name="search", type=str, required=False),
    ],
    responses={200: Envelope},
)

admin_company_detail_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: retrieve a company",
    responses={200: Envelope},
)

admin_company_verify_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: verify a company",
    request=CompanyVerificationSerializer,
    responses={200: Envelope},
)

admin_company_reject_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: reject a company",
    request=CompanyVerificationSerializer,
    responses={200: Envelope},
)

admin_company_suspend_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: suspend a company",
    request=CompanyVerificationSerializer,
    responses={200: Envelope},
)

admin_company_dashboard_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: platform-wide company dashboard summary",
    responses={200: Envelope},
)
