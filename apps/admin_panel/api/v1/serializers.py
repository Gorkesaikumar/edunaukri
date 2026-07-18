from rest_framework import serializers

from apps.admin_panel.models import PlatformSetting


class PlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = (
            "id",
            "key",
            "category",
            "value",
            "description",
            "is_active",
            "updated_at",
        )
        read_only_fields = fields


class PlatformSettingUpdateSerializer(serializers.Serializer):
    value = serializers.DictField()
    description = serializers.CharField(required=False, allow_blank=True)


class UserLifecycleSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["activate", "suspend", "deactivate"])


class AdminRemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True)


class AdminRefundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField()
    reference_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class AdminClaimApproveSerializer(serializers.Serializer):
    resolution = serializers.CharField()
    review_notes = serializers.CharField(required=False, allow_blank=True)


class AdminClaimNotesSerializer(serializers.Serializer):
    review_notes = serializers.CharField(required=False, allow_blank=True)


class AdminPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8, write_only=True)


class AdminFeatureSerializer(serializers.Serializer):
    is_featured = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True)


class AdminCompanySummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    logo_url = serializers.CharField(source="logo.url", allow_null=True, read_only=True)
    website = serializers.CharField()
    industry = serializers.CharField()
    verification_status = serializers.CharField()


class AdminCollegeSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    logo_url = serializers.CharField(source="logo.url", allow_null=True, read_only=True)
    website = serializers.CharField()
    institution_type = serializers.CharField()
    verification_status = serializers.CharField()


class AdminRecruiterSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")
    email = serializers.EmailField(source="user.email")
    phone_number = serializers.CharField(source="user.phone_number", allow_null=True)
    is_verified = serializers.BooleanField(source="user.is_verified")


from apps.applications.api.v1.serializers import (
    JobApplicationSerializer,
    FacultyApplicationSerializer,
)
from apps.it_recruitment.services.jobseeker_portal_helpers import media_url


class AdminJobApplicationSerializer(JobApplicationSerializer):
    applicant_details = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()

    class Meta(JobApplicationSerializer.Meta):
        fields = JobApplicationSerializer.Meta.fields + (
            "applicant_details",
            "resume_url",
        )

    def get_resume_url(self, obj):
        return media_url(getattr(obj, "resume_file", None))

    def get_applicant_details(self, obj):
        profile = obj.job_seeker
        if not profile:
            return None
        return {
            "first_name": getattr(profile, "first_name", "")
            or getattr(profile.user, "first_name", ""),
            "last_name": getattr(profile, "last_name", "")
            or getattr(profile.user, "last_name", ""),
            "email": getattr(profile.user, "email", ""),
            "phone_number": getattr(profile, "phone", "")
            or getattr(profile.user, "phone_number", ""),
            "avatar_url": media_url(getattr(profile, "profile_photo", None)),
            "resume_url": media_url(getattr(obj, "resume_file", None)),
            "designation": getattr(profile, "headline", ""),
            "company": getattr(profile, "current_company", ""),
            "location": getattr(profile, "current_location", ""),
            "experience": getattr(profile, "experience_years", None),
        }


class AdminFacultyApplicationSerializer(FacultyApplicationSerializer):
    applicant_details = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()

    class Meta(FacultyApplicationSerializer.Meta):
        fields = FacultyApplicationSerializer.Meta.fields + (
            "applicant_details",
            "resume_url",
        )

    def get_resume_url(self, obj):
        return media_url(getattr(obj, "cv_file", None))

    def get_applicant_details(self, obj):
        profile = obj.professor
        if not profile:
            return None
        return {
            "first_name": getattr(profile, "first_name", "")
            or getattr(profile.user, "first_name", ""),
            "last_name": getattr(profile, "last_name", "")
            or getattr(profile.user, "last_name", ""),
            "email": getattr(profile.user, "email", ""),
            "phone_number": getattr(profile, "phone", "")
            or getattr(profile.user, "phone_number", ""),
            "avatar_url": media_url(getattr(profile, "profile_photo", None)),
            "resume_url": media_url(getattr(obj, "cv_file", None)),
            "designation": getattr(profile, "current_designation", ""),
            "institution": getattr(profile, "current_institution", ""),
            "location": getattr(profile, "current_location", ""),
            "experience": getattr(profile, "experience_years", None),
        }
