from rest_framework import serializers

from apps.academic_recruitment.api.v1.profile_serializers import (
    CollegeSerializer,
    ProfessorProfileSerializer,
)
from apps.faculty.models import FacultyVacancy


class FacultyVacancySerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyVacancy
        fields = (
            "id",
            "college",
            "title",
            "slug",
            "description",
            "requirements",
            "employment_type",
            "experience_min",
            "salary_min",
            "salary_max",
            "salary_currency",
            "status",
            "published_at",
            "college_name_snapshot",
            "application_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "status",
            "published_at",
            "college_name_snapshot",
            "application_count",
            "created_at",
        )


class FacultyVacancyCreateSerializer(serializers.Serializer):
    college_id = serializers.UUIDField()
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()
    department = serializers.CharField(required=False, allow_blank=True, max_length=200)
    requirements = serializers.CharField(required=False, allow_blank=True)
    employment_type = serializers.CharField(required=False)
    experience_min = serializers.IntegerField(required=False, allow_null=True)
    salary_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class FacultyVacancyUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False)
    requirements = serializers.CharField(required=False, allow_blank=True)
    employment_type = serializers.CharField(required=False)
    experience_min = serializers.IntegerField(required=False, allow_null=True)
    salary_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
