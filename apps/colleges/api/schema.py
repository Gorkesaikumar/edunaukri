from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers

from apps.colleges.api.v1.serializers import (
    DepartmentAddSerializer,
    InstitutionBrandingSerializer,
    InstitutionCampusWriteSerializer,
    InstitutionCreateSerializer,
    InstitutionDocumentUploadSerializer,
    InstitutionMemberAddSerializer,
    InstitutionUpdateSerializer,
    InstitutionVerificationSerializer,
)

TAG = "institutions"
ADMIN_TAG = "admin-institutions"

Envelope = inline_serializer(
    name="InstitutionEnvelope",
    fields={"success": serializers.BooleanField(), "data": serializers.JSONField()},
)


institution_list_schema = extend_schema(
    tags=[TAG],
    summary="List institutions for the authenticated college user",
    parameters=[OpenApiParameter(name="search", type=str, required=False)],
    responses={200: Envelope},
)

institution_create_schema = extend_schema(
    tags=[TAG],
    summary="Create an institution",
    request=InstitutionCreateSerializer,
    responses={201: Envelope},
)

institution_detail_schema = extend_schema(
    tags=[TAG], summary="Retrieve an institution", responses={200: Envelope}
)

institution_update_schema = extend_schema(
    tags=[TAG],
    summary="Update an institution",
    request=InstitutionUpdateSerializer,
    responses={200: Envelope},
)

institution_delete_schema = extend_schema(
    tags=[TAG],
    summary="Soft delete an institution (owner only)",
    responses={200: Envelope},
)

institution_activate_schema = extend_schema(
    tags=[TAG], summary="Activate an institution", responses={200: Envelope}
)

institution_deactivate_schema = extend_schema(
    tags=[TAG], summary="Deactivate an institution", responses={200: Envelope}
)

institution_branding_schema = extend_schema(
    tags=[TAG],
    summary="Update institution logo and/or cover banner",
    request=InstitutionBrandingSerializer,
    responses={200: Envelope},
)

institution_dashboard_schema = extend_schema(
    tags=[TAG],
    summary="Institution dashboard summary for the college user",
    responses={200: Envelope},
)

institution_department_list_schema = extend_schema(
    tags=[TAG], summary="List institution departments", responses={200: Envelope}
)

institution_department_add_schema = extend_schema(
    tags=[TAG],
    summary="Add a department to the institution",
    request=DepartmentAddSerializer,
    responses={201: Envelope},
)

institution_department_remove_schema = extend_schema(
    tags=[TAG],
    summary="Remove a department from the institution",
    responses={200: Envelope},
)

institution_campus_list_schema = extend_schema(
    tags=[TAG], summary="List institution campuses", responses={200: Envelope}
)

institution_campus_create_schema = extend_schema(
    tags=[TAG],
    summary="Add an institution campus",
    request=InstitutionCampusWriteSerializer,
    responses={201: Envelope},
)

institution_campus_detail_schema = extend_schema(
    tags=[TAG],
    summary="Update or delete an institution campus",
    request=InstitutionCampusWriteSerializer,
    responses={200: Envelope},
)

institution_member_list_schema = extend_schema(
    tags=[TAG],
    summary="List institution members (college users)",
    responses={200: Envelope},
)

institution_member_add_schema = extend_schema(
    tags=[TAG],
    summary="Add a college user to the institution (admin only)",
    request=InstitutionMemberAddSerializer,
    responses={201: Envelope},
)

institution_member_remove_schema = extend_schema(
    tags=[TAG],
    summary="Remove a college user from the institution (admin only)",
    responses={200: Envelope},
)

institution_document_list_schema = extend_schema(
    tags=[TAG], summary="List institution documents", responses={200: Envelope}
)

institution_document_upload_schema = extend_schema(
    tags=[TAG],
    summary="Attach a document to the institution",
    request=InstitutionDocumentUploadSerializer,
    responses={201: Envelope},
)

institution_document_remove_schema = extend_schema(
    tags=[TAG], summary="Remove an institution document", responses={200: Envelope}
)


admin_institution_list_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: list all institutions",
    parameters=[
        OpenApiParameter(name="status", type=str, required=False),
        OpenApiParameter(name="is_active", type=bool, required=False),
        OpenApiParameter(name="search", type=str, required=False),
    ],
    responses={200: Envelope},
)

admin_institution_detail_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: retrieve an institution",
    responses={200: Envelope},
)

admin_institution_verify_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: verify an institution",
    request=InstitutionVerificationSerializer,
    responses={200: Envelope},
)

admin_institution_reject_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: reject an institution",
    request=InstitutionVerificationSerializer,
    responses={200: Envelope},
)

admin_institution_suspend_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: suspend an institution",
    request=InstitutionVerificationSerializer,
    responses={200: Envelope},
)

admin_institution_dashboard_schema = extend_schema(
    tags=[ADMIN_TAG],
    summary="Admin: platform-wide institution dashboard summary",
    responses={200: Envelope},
)
