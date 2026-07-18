from rest_framework import serializers

from apps.companies.models import Company, CompanyLocation, CompanyMember


class CompanyLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyLocation
        fields = (
            "id",
            "label",
            "address_line",
            "city",
            "state",
            "country",
            "postal_code",
            "is_headquarters",
        )
        read_only_fields = ("id",)


class CompanyMemberSerializer(serializers.ModelSerializer):
    recruiter_id = serializers.UUIDField(source="recruiter.id", read_only=True)

    class Meta:
        model = CompanyMember
        fields = ("id", "recruiter_id", "role", "is_primary", "is_active")
        read_only_fields = fields


class CompanySerializer(serializers.ModelSerializer):
    logo_file_id = serializers.UUIDField(read_only=True)
    cover_banner_file_id = serializers.UUIDField(read_only=True)
    locations = CompanyLocationSerializer(many=True, read_only=True)

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "legal_name",
            "slug",
            "description",
            "mission",
            "vision",
            "benefits",
            "culture",
            "industry",
            "organization_type",
            "company_size",
            "founded_year",
            "gst_number",
            "website_url",
            "email",
            "phone",
            "logo_file_id",
            "cover_banner_file_id",
            "headquarters_location",
            "address_line",
            "city",
            "state",
            "country",
            "postal_code",
            "linkedin_url",
            "twitter_url",
            "facebook_url",
            "instagram_url",
            "youtube_url",
            "is_active",
            "verification_status",
            "verification_remarks",
            "verified_at",
            "locations",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "logo_file_id",
            "cover_banner_file_id",
            "is_active",
            "verification_status",
            "verification_remarks",
            "verified_at",
            "locations",
            "created_at",
            "updated_at",
        )


from apps.core.validators.common import validate_clean_text, validate_organization_name, validate_gst, validate_phone

class _CompanyWritableSerializer(serializers.Serializer):
    """Shared writable fields for create/update payloads."""

    legal_name = serializers.CharField(max_length=300, required=False, allow_blank=True, validators=[validate_organization_name])
    description = serializers.CharField(required=False, allow_blank=True, validators=[validate_clean_text])
    mission = serializers.CharField(required=False, allow_blank=True, validators=[validate_clean_text])
    vision = serializers.CharField(required=False, allow_blank=True, validators=[validate_clean_text])
    benefits = serializers.CharField(required=False, allow_blank=True, validators=[validate_clean_text])
    culture = serializers.CharField(required=False, allow_blank=True, validators=[validate_clean_text])
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True)
    organization_type = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )
    company_size = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    founded_year = serializers.IntegerField(required=False, allow_null=True)
    gst_number = serializers.CharField(max_length=20, required=False, allow_blank=True, validators=[validate_gst])
    website_url = serializers.URLField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, validators=[validate_phone])
    headquarters_location = serializers.CharField(
        max_length=200, required=False, allow_blank=True, validators=[validate_clean_text]
    )
    address_line = serializers.CharField(
        max_length=300, required=False, allow_blank=True, validators=[validate_clean_text]
    )
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    twitter_url = serializers.URLField(required=False, allow_blank=True)
    facebook_url = serializers.URLField(required=False, allow_blank=True)
    instagram_url = serializers.URLField(required=False, allow_blank=True)
    youtube_url = serializers.URLField(required=False, allow_blank=True)


class CompanyCreateSerializer(_CompanyWritableSerializer):
    name = serializers.CharField(max_length=300, validators=[validate_organization_name])


class CompanyUpdateSerializer(_CompanyWritableSerializer):
    name = serializers.CharField(max_length=300, required=False, validators=[validate_organization_name])


class CompanyBrandingSerializer(serializers.Serializer):
    logo_file_id = serializers.UUIDField(required=False)
    banner_file_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get("logo_file_id") and not attrs.get("banner_file_id"):
            raise serializers.ValidationError(
                "Provide logo_file_id and/or banner_file_id."
            )
        return attrs


class CompanyVerificationSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CompanyLocationWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    address_line = serializers.CharField(
        max_length=300, required=False, allow_blank=True
    )
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=120, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_headquarters = serializers.BooleanField(required=False, default=False)


class CompanyMemberAddSerializer(serializers.Serializer):
    recruiter_email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=["admin", "recruiter"], required=False, default="recruiter"
    )
