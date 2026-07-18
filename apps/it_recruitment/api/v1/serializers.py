from rest_framework import serializers

from apps.companies.models import Company
from apps.it_recruitment.api.v1.profile_serializers import (
    JobSeekerProfileSerializer,
    RecruiterProfileSerializer,
)
from apps.jobs.models import JobPosting, Skill


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "slug",
            "description",
            "industry",
            "company_size",
            "website_url",
            "headquarters_location",
            "is_active",
            "created_at",
        )
        read_only_fields = ("id", "slug", "is_active", "created_at")


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ("id", "name", "category")


class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = (
            "id",
            "company",
            "title",
            "slug",
            "description",
            "requirements",
            "employment_type",
            "experience_min",
            "experience_max",
            "salary_min",
            "salary_max",
            "salary_currency",
            "location",
            "is_remote",
            "status",
            "published_at",
            "company_name_snapshot",
            "application_count",
            "created_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "status",
            "published_at",
            "company_name_snapshot",
            "application_count",
            "created_at",
        )


class JobPostingCreateSerializer(serializers.Serializer):
    company_id = serializers.UUIDField()
    title = serializers.CharField(max_length=300)
    description = serializers.CharField()
    requirements = serializers.CharField(required=False, allow_blank=True)
    employment_type = serializers.CharField(required=False)
    experience_min = serializers.IntegerField(required=False, allow_null=True)
    experience_max = serializers.IntegerField(required=False, allow_null=True)
    salary_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    location = serializers.CharField(required=False, allow_blank=True)
    is_remote = serializers.BooleanField(required=False, default=False)


class JobPostingUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False)
    requirements = serializers.CharField(required=False, allow_blank=True)
    employment_type = serializers.CharField(required=False)
    experience_min = serializers.IntegerField(required=False, allow_null=True)
    experience_max = serializers.IntegerField(required=False, allow_null=True)
    salary_min = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    salary_max = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    location = serializers.CharField(required=False, allow_blank=True)
    is_remote = serializers.BooleanField(required=False)


class CompanyUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=300, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    industry = serializers.CharField(required=False, allow_blank=True)
    company_size = serializers.CharField(required=False, allow_blank=True)
    website_url = serializers.URLField(required=False, allow_blank=True)
    headquarters_location = serializers.CharField(required=False, allow_blank=True)
