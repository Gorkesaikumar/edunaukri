from rest_framework import serializers

from apps.faculty.constants.enums import (
    Designation,
    EmploymentType,
    QualificationLevel,
    RecruitmentCategory,
    SalaryVisibility,
    VacancyVisibility,
    WorkType,
)
from apps.faculty.models import FacultyVacancy, FacultyVacancyCampus


class FacultyVacancyCampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyVacancyCampus
        fields = (
            "id",
            "country",
            "state",
            "district",
            "city",
            "campus",
            "work_type",
            "is_primary",
        )
        read_only_fields = ("id",)


class FacultyVacancySerializer(serializers.ModelSerializer):
    college_id = serializers.UUIDField(read_only=True)
    campuses = FacultyVacancyCampusSerializer(many=True, read_only=True)

    class Meta:
        model = FacultyVacancy
        fields = (
            "id",
            "college_id",
            "title",
            "slug",
            "vacancy_code",
            "department",
            "designation",
            "description",
            "requirements",
            "roles_responsibilities",
            "teaching_responsibilities",
            "research_expectations",
            "administrative_responsibilities",
            "benefits",
            "facilities",
            "accommodation",
            "employment_type",
            "work_type",
            "recruitment_category",
            "contract_duration",
            "minimum_qualification",
            "preferred_qualification",
            "qualification_required",
            "specialization_required",
            "experience_min",
            "experience_max",
            "research_experience",
            "industry_experience",
            "salary_min",
            "salary_max",
            "salary_currency",
            "salary_visibility",
            "vacancy_count",
            "joining_date",
            "application_deadline",
            "hiring_committee",
            "country",
            "state",
            "district",
            "city",
            "campus",
            "visibility",
            "is_featured",
            "is_urgent",
            "is_template",
            "status",
            "published_at",
            "expires_at",
            "closed_at",
            "college_name_snapshot",
            "application_count",
            "view_count",
            "moderation_status",
            "campuses",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class _VacancyWritableSerializer(serializers.Serializer):
    vacancy_code = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    department = serializers.CharField(max_length=200, required=False, allow_blank=True)
    designation = serializers.ChoiceField(
        choices=Designation.choices, required=False, allow_blank=True
    )
    requirements = serializers.CharField(required=False, allow_blank=True)
    roles_responsibilities = serializers.CharField(required=False, allow_blank=True)
    teaching_responsibilities = serializers.CharField(required=False, allow_blank=True)
    research_expectations = serializers.CharField(required=False, allow_blank=True)
    administrative_responsibilities = serializers.CharField(
        required=False, allow_blank=True
    )
    benefits = serializers.CharField(required=False, allow_blank=True)
    facilities = serializers.CharField(required=False, allow_blank=True)
    accommodation = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    employment_type = serializers.ChoiceField(
        choices=EmploymentType.choices, required=False
    )
    work_type = serializers.ChoiceField(choices=WorkType.choices, required=False)
    recruitment_category = serializers.ChoiceField(
        choices=RecruitmentCategory.choices, required=False, allow_blank=True
    )
    contract_duration = serializers.CharField(
        max_length=120, required=False, allow_blank=True
    )
    minimum_qualification = serializers.ChoiceField(
        choices=QualificationLevel.choices, required=False, allow_blank=True
    )
    preferred_qualification = serializers.ChoiceField(
        choices=QualificationLevel.choices, required=False, allow_blank=True
    )
    qualification_required = serializers.CharField(required=False, allow_blank=True)
    specialization_required = serializers.CharField(required=False, allow_blank=True)
    experience_min = serializers.IntegerField(required=False, allow_null=True)
    experience_max = serializers.IntegerField(required=False, allow_null=True)
    research_experience = serializers.IntegerField(required=False, allow_null=True)
    industry_experience = serializers.IntegerField(required=False, allow_null=True)
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
    vacancy_count = serializers.IntegerField(required=False)
    joining_date = serializers.DateField(required=False, allow_null=True)
    application_deadline = serializers.DateTimeField(required=False, allow_null=True)
    hiring_committee = serializers.CharField(
        max_length=300, required=False, allow_blank=True
    )
    country = serializers.CharField(max_length=120, required=False, allow_blank=True)
    state = serializers.CharField(max_length=120, required=False, allow_blank=True)
    district = serializers.CharField(max_length=120, required=False, allow_blank=True)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    campus = serializers.CharField(max_length=200, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=VacancyVisibility.choices, required=False
    )
    is_template = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    campuses = serializers.ListField(child=serializers.DictField(), required=False)


class FacultyVacancyCreateSerializer(_VacancyWritableSerializer):
    college_id = serializers.UUIDField()
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()


class FacultyVacancyUpdateSerializer(_VacancyWritableSerializer):
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False)


class VacancyVisibilitySerializer(serializers.Serializer):
    is_featured = serializers.BooleanField(required=False)
    is_urgent = serializers.BooleanField(required=False)
    visibility = serializers.ChoiceField(
        choices=VacancyVisibility.choices, required=False
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one visibility field.")
        return attrs


class VacancyModerationSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
