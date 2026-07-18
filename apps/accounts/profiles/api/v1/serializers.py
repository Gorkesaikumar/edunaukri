from rest_framework import serializers

from apps.academic_recruitment.models import ProfessorProfile
from apps.colleges.models import College
from apps.it_recruitment.models import (
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProfile,
    RecruiterProfile,
)
from apps.it_recruitment.models.profiles import JobSeekerCertification, JobSeekerProject


class JobSeekerExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSeekerExperience
        fields = (
            "id",
            "company_name",
            "title",
            "employment_type",
            "location",
            "start_date",
            "end_date",
            "is_current",
            "description",
        )
        read_only_fields = fields


class JobSeekerEducationSerializer(serializers.ModelSerializer):
    education_level_label = serializers.CharField(source="level_label", read_only=True)
    score_display = serializers.CharField(read_only=True)
    year_display = serializers.CharField(read_only=True)

    class Meta:
        model = JobSeekerEducation
        fields = (
            "id",
            "education_level",
            "education_level_label",
            "institution",
            "university",
            "college",
            "board",
            "stream",
            "degree_type",
            "score_type",
            "degree",
            "field_of_study",
            "percentage",
            "cgpa",
            "passing_year",
            "start_year",
            "end_year",
            "grade",
            "score_display",
            "year_display",
        )
        read_only_fields = fields


class JobSeekerProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSeekerProject
        fields = (
            "id",
            "title",
            "description",
            "technologies",
            "project_url",
            "github_url",
        )
        read_only_fields = fields


class JobSeekerCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobSeekerCertification
        fields = (
            "id",
            "name",
            "issuing_organization",
            "issue_date",
            "credential_id",
            "credential_url",
        )
        read_only_fields = fields


class JobSeekerProfileSerializer(serializers.ModelSerializer):
    skills = serializers.SerializerMethodField()

    class Meta:
        model = JobSeekerProfile
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone",
            "gender",
            "date_of_birth",
            "city",
            "state",
            "country",
            "headline",
            "summary",
            "experience_years",
            "current_location",
            "preferred_location",
            "current_company",
            "current_salary",
            "expected_salary",
            "notice_period_days",
            "employment_type_preference",
            "work_mode_preference",
            "preferred_roles",
            "linkedin_url",
            "github_url",
            "portfolio_url",
            "personal_website",
            "languages",
            "profile_photo_id",
            "resume_file_id",
            "profile_completeness",
            "profile_status",
            "profile_visibility",
            "skills",
            "experiences",
            "education",
            "projects",
            "certifications",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "profile_completeness",
            "created_at",
            "updated_at",
        )

    def get_skills(self, obj) -> list[str]:
        return list(
            obj.skills.filter(is_deleted=False)
            .select_related("skill")
            .values_list("skill__name", flat=True)
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["experiences"] = JobSeekerExperienceSerializer(
            instance.experiences.filter(is_deleted=False), many=True
        ).data
        data["education"] = JobSeekerEducationSerializer(
            instance.education.filter(is_deleted=False), many=True
        ).data
        data["projects"] = JobSeekerProjectSerializer(
            instance.projects.filter(is_deleted=False), many=True
        ).data
        data["certifications"] = JobSeekerCertificationSerializer(
            instance.certifications.filter(is_deleted=False), many=True
        ).data
        return data


class RecruiterProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterProfile
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone",
            "official_email",
            "designation",
            "department",
            "company_association",
            "profile_image_id",
            "profile_status",
            "profile_visibility",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ProfessorProfileSerializer(serializers.ModelSerializer):
    department_ids = serializers.SerializerMethodField()
    qualifications = serializers.SerializerMethodField()

    class Meta:
        model = ProfessorProfile
        fields = (
            "id",
            "first_name",
            "last_name",
            "phone",
            "highest_qualification",
            "specialization",
            "research_interests",
            "experience_years",
            "teaching_experience_years",
            "industry_experience_years",
            "publications_count",
            "current_designation",
            "current_institution",
            "expected_salary",
            "preferred_locations",
            "profile_photo_id",
            "cv_file_id",
            "profile_completeness",
            "profile_status",
            "profile_visibility",
            "department_ids",
            "qualifications",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "profile_completeness", "created_at", "updated_at")

    def get_department_ids(self, obj):
        return list(
            obj.departments.filter(is_deleted=False).values_list(
                "department_id", flat=True
            )
        )

    def get_qualifications(self, obj):
        return [
            {
                "name": row.qualification.name,
                "institution_name": row.institution_name,
                "year_obtained": row.year_obtained,
            }
            for row in obj.qualifications.filter(is_deleted=False).select_related(
                "qualification"
            )
        ]


class CollegeProfileSerializer(serializers.ModelSerializer):
    department_ids = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = (
            "id",
            "name",
            "slug",
            "college_type",
            "description",
            "website_url",
            "address_line",
            "city",
            "state",
            "pin_code",
            "accreditation",
            "aicte_code",
            "ugc_code",
            "naac_grade",
            "contact_phone",
            "contact_email",
            "established_year",
            "logo_file_id",
            "profile_status",
            "profile_visibility",
            "department_ids",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "slug", "created_at", "updated_at")

    def get_department_ids(self, obj):
        return list(
            obj.departments.filter(is_deleted=False).values_list(
                "department_id", flat=True
            )
        )


class AdminProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    domain = serializers.CharField()
    is_staff = serializers.BooleanField()
    is_superuser = serializers.BooleanField()


class ProfileCompletionSerializer(serializers.Serializer):
    profile_type = serializers.CharField()
    completion_percentage = serializers.IntegerField()


class ProfileStatisticsSerializer(serializers.Serializer):
    overview = serializers.DictField()
    average_completion = serializers.DictField()
