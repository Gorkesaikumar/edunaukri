from rest_framework import serializers

from apps.jobs.constants.enums import (
    EmploymentType,
    JobVisibility,
    SalaryVisibility,
    WorkMode,
)
from apps.jobs.models import JobLocation, JobPosting


class JobLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobLocation
        fields = (
            "id",
            "country",
            "state",
            "city",
            "office_address",
            "work_mode",
            "is_primary",
        )
        read_only_fields = ("id",)


class JobSkillSerializer(serializers.Serializer):
    name = serializers.CharField()
    category = serializers.CharField(allow_blank=True)
    is_preferred = serializers.BooleanField()


class JobPostingSerializer(serializers.ModelSerializer):
    company_id = serializers.UUIDField(read_only=True)
    locations = JobLocationSerializer(many=True, read_only=True)
    required_skill_names = serializers.SerializerMethodField()
    preferred_skill_names = serializers.SerializerMethodField()

    class Meta:
        model = JobPosting
        fields = (
            "id",
            "company_id",
            "title",
            "slug",
            "job_code",
            "category",
            "department",
            "description",
            "requirements",
            "roles_responsibilities",
            "benefits",
            "education_requirement",
            "employment_type",
            "work_mode",
            "experience_min",
            "experience_max",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_visibility",
            "vacancies",
            "joining_timeline",
            "application_deadline",
            "hiring_manager",
            "country",
            "state",
            "city",
            "office_address",
            "location",
            "is_remote",
            "visibility",
            "is_featured",
            "is_urgent",
            "is_template",
            "status",
            "published_at",
            "expires_at",
            "closed_at",
            "company_name_snapshot",
            "application_count",
            "view_count",
            "moderation_status",
            "locations",
            "required_skill_names",
            "preferred_skill_names",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def _skill_names(self, obj, *, preferred: bool):
        # ``required_skills`` uses the active (non-deleted) default manager, so
        # ``.all()`` is prefetch-friendly and excludes soft-deleted links.
        return [
            link.skill.name
            for link in obj.required_skills.all()
            if link.is_preferred == preferred
        ]

    def get_required_skill_names(self, obj):
        return self._skill_names(obj, preferred=False)

    def get_preferred_skill_names(self, obj):
        return self._skill_names(obj, preferred=True)


class _JobWritableSerializer(serializers.Serializer):
    job_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    category = serializers.CharField(max_length=150, required=False, allow_blank=True)
    department = serializers.CharField(max_length=150, required=False, allow_blank=True)
    requirements = serializers.CharField(required=False, allow_blank=True)
    roles_responsibilities = serializers.CharField(required=False, allow_blank=True)
    benefits = serializers.CharField(required=False, allow_blank=True)
    education_requirement = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    employment_type = serializers.ChoiceField(
        choices=EmploymentType.choices, required=False
    )
    work_mode = serializers.ChoiceField(choices=WorkMode.choices, required=False)
    experience_min = serializers.IntegerField(required=False, allow_null=True)
    experience_max = serializers.IntegerField(required=False, allow_null=True)
    salary_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    salary_currency = serializers.CharField(max_length=3, required=False)
    salary_visibility = serializers.ChoiceField(
        choices=SalaryVisibility.choices, required=False
    )
    vacancies = serializers.IntegerField(required=False)
    joining_timeline = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    application_deadline = serializers.DateTimeField(required=False, allow_null=True)
    hiring_manager = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=120, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    office_address = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    is_remote = serializers.BooleanField(required=False)
    visibility = serializers.ChoiceField(choices=JobVisibility.choices, required=False)
    is_template = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    required_skills = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    preferred_skills = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    locations = serializers.ListField(child=serializers.DictField(), required=False)


class JobCreateSerializer(_JobWritableSerializer):
    company_id = serializers.UUIDField()
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()


class JobUpdateSerializer(_JobWritableSerializer):
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False)


class JobVisibilitySerializer(serializers.Serializer):
    is_featured = serializers.BooleanField(required=False)
    is_urgent = serializers.BooleanField(required=False)
    visibility = serializers.ChoiceField(choices=JobVisibility.choices, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one visibility field.")
        return attrs


class JobModerationSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
