from rest_framework import serializers

from apps.colleges.models import (
    College,
    CollegeMember,
    InstitutionCampus,
    InstitutionDocument,
)


class InstitutionCampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstitutionCampus
        fields = (
            "id",
            "label",
            "address_line",
            "city",
            "district",
            "state",
            "country",
            "pin_code",
            "latitude",
            "longitude",
            "is_main_campus",
        )
        read_only_fields = ("id",)


class InstitutionMemberSerializer(serializers.ModelSerializer):
    college_user_id = serializers.UUIDField(source="college_user.id", read_only=True)

    class Meta:
        model = CollegeMember
        fields = ("id", "college_user_id", "role", "is_primary", "is_active")
        read_only_fields = fields


class InstitutionDocumentSerializer(serializers.ModelSerializer):
    stored_file_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = InstitutionDocument
        fields = ("id", "document_type", "stored_file_id", "title", "created_at")
        read_only_fields = fields


class InstitutionSerializer(serializers.ModelSerializer):
    logo_file_id = serializers.UUIDField(read_only=True)
    cover_banner_file_id = serializers.UUIDField(read_only=True)
    department_ids = serializers.SerializerMethodField()
    campuses = InstitutionCampusSerializer(many=True, read_only=True)

    class Meta:
        model = College
        fields = (
            "id",
            "name",
            "legal_name",
            "slug",
            "college_type",
            "institution_type",
            "ownership_type",
            "autonomous_status",
            "description",
            "vision",
            "mission",
            "infrastructure_description",
            "facilities",
            "placement_cell_details",
            "research_centers",
            "hostel_availability",
            "transportation_facilities",
            "affiliated_university",
            "academic_calendar_reference",
            "programs_offered",
            "courses_offered",
            "accreditation",
            "aicte_code",
            "ugc_code",
            "naac_grade",
            "nba_accreditation",
            "established_year",
            "campus_area",
            "number_of_students",
            "number_of_faculty",
            "website_url",
            "contact_email",
            "contact_phone",
            "alternate_phone",
            "logo_file_id",
            "cover_banner_file_id",
            "address_line",
            "city",
            "district",
            "state",
            "country",
            "pin_code",
            "latitude",
            "longitude",
            "linkedin_url",
            "facebook_url",
            "instagram_url",
            "twitter_url",
            "youtube_url",
            "is_active",
            "profile_status",
            "profile_visibility",
            "verification_status",
            "verification_remarks",
            "verified_at",
            "department_ids",
            "campuses",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "logo_file_id",
            "cover_banner_file_id",
            "is_active",
            "profile_status",
            "verification_status",
            "verification_remarks",
            "verified_at",
            "department_ids",
            "campuses",
            "created_at",
            "updated_at",
        )

    def get_department_ids(self, obj):
        return list(
            obj.departments.filter(is_deleted=False).values_list(
                "department_id", flat=True
            )
        )


class _InstitutionWritableSerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=300, required=False, allow_blank=True)
    college_type = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    institution_type = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )
    ownership_type = serializers.CharField(
        max_length=30, required=False, allow_blank=True
    )
    autonomous_status = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    vision = serializers.CharField(required=False, allow_blank=True)
    mission = serializers.CharField(required=False, allow_blank=True)
    infrastructure_description = serializers.CharField(required=False, allow_blank=True)
    facilities = serializers.CharField(required=False, allow_blank=True)
    placement_cell_details = serializers.CharField(required=False, allow_blank=True)
    research_centers = serializers.CharField(required=False, allow_blank=True)
    hostel_availability = serializers.BooleanField(required=False)
    transportation_facilities = serializers.BooleanField(required=False)
    affiliated_university = serializers.CharField(
        max_length=300, required=False, allow_blank=True
    )
    academic_calendar_reference = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    programs_offered = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    courses_offered = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    accreditation = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    aicte_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    ugc_code = serializers.CharField(max_length=100, required=False, allow_blank=True)
    naac_grade = serializers.CharField(max_length=10, required=False, allow_blank=True)
    nba_accreditation = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    established_year = serializers.IntegerField(required=False, allow_null=True)
    campus_area = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    number_of_students = serializers.IntegerField(required=False, allow_null=True)
    number_of_faculty = serializers.IntegerField(required=False, allow_null=True)
    website_url = serializers.URLField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    alternate_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    address_line = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    district = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    pin_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    facebook_url = serializers.URLField(required=False, allow_blank=True)
    instagram_url = serializers.URLField(required=False, allow_blank=True)
    twitter_url = serializers.URLField(required=False, allow_blank=True)
    youtube_url = serializers.URLField(required=False, allow_blank=True)
    profile_visibility = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )


class InstitutionCreateSerializer(_InstitutionWritableSerializer):
    name = serializers.CharField(max_length=300)


class InstitutionUpdateSerializer(_InstitutionWritableSerializer):
    name = serializers.CharField(max_length=300, required=False)


class InstitutionBrandingSerializer(serializers.Serializer):
    logo_file_id = serializers.UUIDField(required=False)
    banner_file_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs.get("logo_file_id") and not attrs.get("banner_file_id"):
            raise serializers.ValidationError(
                "Provide logo_file_id and/or banner_file_id."
            )
        return attrs


class InstitutionVerificationSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class InstitutionCampusWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=150, required=False, allow_blank=True)
    address_line = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    district = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    pin_code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    is_main_campus = serializers.BooleanField(required=False, default=False)


class DepartmentAddSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    category = serializers.CharField(max_length=50, required=False, allow_blank=True)


class InstitutionMemberAddSerializer(serializers.Serializer):
    user_email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=["admin", "member"], required=False, default="member"
    )


class InstitutionDocumentUploadSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(
        choices=[
            "approval_certificate",
            "accreditation_certificate",
            "naac_document",
            "aicte_document",
            "ugc_document",
            "brochure",
            "logo",
            "campus_image",
            "other",
        ]
    )
    stored_file_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
