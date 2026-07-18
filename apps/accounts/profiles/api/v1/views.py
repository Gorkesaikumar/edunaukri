from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import BruteForceIPThrottle, ResumeUploadThrottle

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.profiles.api.schema import (
    admin_profile_detail_schema,
    admin_profile_statistics_schema,
    my_profile_create_schema,
    my_profile_get_schema,
    my_profile_update_schema,
    profile_completion_schema,
    profile_lifecycle_schema,
    public_profile_schema,
)
from apps.accounts.profiles.api.v1.serializers import (
    AdminProfileSerializer,
    CollegeProfileSerializer,
    JobSeekerProfileSerializer,
    ProfessorProfileSerializer,
    ProfileCompletionSerializer,
    ProfileStatisticsSerializer,
    RecruiterProfileSerializer,
)
from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.permissions.profile_permissions import (
    CanManageOwnProfile,
    CanViewAnyProfile,
    IsProfileOwner,
)
from apps.accounts.profiles.selectors.profile_selector import ProfileSelector
from apps.accounts.profiles.selectors.profile_statistics_selector import (
    ProfileStatisticsSelector,
)
from apps.accounts.profiles.services.profile_service import ProfileService
from apps.accounts.profiles.services.profile_visibility_service import (
    ProfileVisibilityService,
)
from apps.core.views.base import EnvelopeAPIView


SERIALIZER_MAP = {
    ProfileType.JOB_SEEKER: JobSeekerProfileSerializer,
    ProfileType.RECRUITER: RecruiterProfileSerializer,
    ProfileType.PROFESSOR: ProfessorProfileSerializer,
    ProfileType.COLLEGE: CollegeProfileSerializer,
    ProfileType.ADMIN: AdminProfileSerializer,
}


class MyProfileView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ResumeUploadThrottle, BruteForceIPThrottle]

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), CanManageOwnProfile()]
        if self.request.method == "PATCH":
            return [permissions.IsAuthenticated(), IsProfileOwner()]
        return super().get_permissions()

    @my_profile_get_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        if profile_type == ProfileType.ADMIN:
            admin = request.user
            return self.success_response(
                AdminProfileSerializer(
                    {
                        "id": admin.pk,
                        "email": admin.email,
                        "domain": "admin",
                        "is_staff": admin.is_staff,
                        "is_superuser": admin.is_superuser,
                    }
                ).data
            )
        profile = ProfileService().get_profile(request.user, profile_type)
        if not profile:
            return self.success_response(None)
        serializer_cls = SERIALIZER_MAP[profile_type]
        return self.success_response(serializer_cls(profile).data)

    @my_profile_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        profile = ProfileService().create_profile(user=request.user, data=request.data)
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        return self.success_response(
            SERIALIZER_MAP[profile_type](profile).data, status=status.HTTP_201_CREATED
        )

    @my_profile_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request):
        profile = ProfileService().update_profile(user=request.user, data=request.data)
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        return self.success_response(SERIALIZER_MAP[profile_type](profile).data)


class ProfileCompletionView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]

    @profile_completion_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        data = ProfileService().get_completion(request.user)
        return self.success_response(ProfileCompletionSerializer(data).data)


class ProfileDeactivateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]

    @profile_lifecycle_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        if profile_type == ProfileType.ADMIN:
            return self.error_response(
                "NOT_SUPPORTED", "Admin profiles cannot be deactivated.", status=400
            )
        profile = ProfileService().deactivate_profile(request.user, profile_type)
        return self.success_response(SERIALIZER_MAP[profile_type](profile).data)


class ProfileActivateView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]

    @profile_lifecycle_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        profile_type = ProfileSelector().resolve_profile_type(request.user)
        profile = ProfileService().activate_profile(request.user, profile_type)
        return self.success_response(SERIALIZER_MAP[profile_type](profile).data)


class PublicProfileView(EnvelopeAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BruteForceIPThrottle]

    @public_profile_schema
    @extend_schema(responses={200: dict})
    def get(self, request, profile_type, profile_id):
        try:
            profile_type_enum = ProfileType(profile_type)
        except ValueError:
            return self.error_response(
                "INVALID_TYPE", "Invalid profile type.", status=400
            )
        profile = ProfileSelector().get_public_profile(profile_type_enum, profile_id)
        viewer = request.user if request.user.is_authenticated else None
        if profile_type_enum == ProfileType.JOB_SEEKER:
            from apps.it_recruitment.services.jobseeker_privacy_service import (
                JobSeekerPrivacyService,
            )

            privacy = JobSeekerPrivacyService()
            visibility = ProfileVisibilityService()
            if not privacy.is_admin(viewer):
                privacy.ensure_can_view_profile(profile, viewer)
            data = JobSeekerProfileSerializer(profile).data
            if not privacy.is_admin(viewer):
                data = privacy.mask_profile_data(profile, viewer, data)
                data = visibility.to_public_dict(data, profile_type_enum)
            return self.success_response(data)

        visibility = ProfileVisibilityService()
        if not isinstance(viewer, AdminUser):
            visibility.ensure_can_view(
                viewer=viewer, profile=profile, profile_type=profile_type_enum
            )
        data = SERIALIZER_MAP[profile_type_enum](profile).data
        if not isinstance(viewer, AdminUser):
            data = visibility.to_public_dict(data, profile_type_enum)
        return self.success_response(data)


class AdminProfileDetailView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, CanViewAnyProfile]

    @admin_profile_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, profile_type, profile_id):
        try:
            profile_type_enum = ProfileType(profile_type)
        except ValueError:
            return self.error_response(
                "INVALID_TYPE", "Invalid profile type.", status=400
            )
        profile = ProfileSelector().get_public_profile(profile_type_enum, profile_id)
        return self.success_response(SERIALIZER_MAP[profile_type_enum](profile).data)


class AdminProfileStatisticsView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, CanViewAnyProfile]

    @admin_profile_statistics_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        selector = ProfileStatisticsSelector()
        data = {
            "overview": selector.overview(),
            "average_completion": selector.average_completion(),
        }
        return self.success_response(ProfileStatisticsSerializer(data).data)
