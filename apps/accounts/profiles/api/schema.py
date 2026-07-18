from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from apps.accounts.profiles.api.v1.serializers import (
    CollegeProfileSerializer,
    JobSeekerProfileSerializer,
    ProfessorProfileSerializer,
    ProfileCompletionSerializer,
    ProfileStatisticsSerializer,
    RecruiterProfileSerializer,
)

ProfileEnvelope = inline_serializer(
    name="ProfileEnvelope",
    fields={
        "success": serializers.BooleanField(),
        "data": serializers.JSONField(),
    },
)

my_profile_get_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Get own profile",
    responses={200: ProfileEnvelope},
)

my_profile_create_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Create own profile",
    request=JobSeekerProfileSerializer,
    responses={201: ProfileEnvelope},
)

my_profile_update_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Update own profile",
    request=JobSeekerProfileSerializer,
    responses={200: ProfileEnvelope},
)

profile_completion_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Get profile completion percentage",
    responses={
        200: inline_serializer(
            name="ProfileCompletionEnvelope",
            fields={
                "success": serializers.BooleanField(),
                "data": ProfileCompletionSerializer(),
            },
        )
    },
)

profile_lifecycle_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Activate or deactivate own profile",
    responses={200: ProfileEnvelope},
)

public_profile_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Get public profile by type and id",
    responses={200: ProfileEnvelope},
)

admin_profile_detail_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Admin: full profile detail",
    responses={200: ProfileEnvelope},
)

admin_profile_statistics_schema = extend_schema(
    tags=["accounts-profiles"],
    summary="Admin: profile statistics overview",
    responses={
        200: inline_serializer(
            name="ProfileStatisticsEnvelope",
            fields={
                "success": serializers.BooleanField(),
                "data": ProfileStatisticsSerializer(),
            },
        )
    },
)

PROFILE_SERIALIZER_BY_TYPE = {
    "job_seeker": JobSeekerProfileSerializer,
    "recruiter": RecruiterProfileSerializer,
    "professor": ProfessorProfileSerializer,
    "college": CollegeProfileSerializer,
}
