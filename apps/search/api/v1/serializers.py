from rest_framework import serializers

from apps.academic_recruitment.models import ProfessorProfile
from apps.applications.models import FacultyApplication, JobApplication
from apps.colleges.models import College
from apps.companies.models import Company
from apps.faculty.models import FacultyVacancy
from apps.guarantee_claims.models import GuaranteeClaim
from apps.invoices.models import Invoice
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.jobs.models import JobPosting


class JobSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = (
            "id",
            "title",
            "slug",
            "company",
            "company_name_snapshot",
            "employment_type",
            "work_mode",
            "location",
            "is_remote",
            "salary_min",
            "salary_max",
            "salary_currency",
            "published_at",
            "application_count",
        )


class VacancySearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyVacancy
        fields = (
            "id",
            "title",
            "slug",
            "college",
            "college_name_snapshot",
            "department",
            "employment_type",
            "experience_min",
            "salary_min",
            "salary_max",
            "salary_currency",
            "published_at",
            "application_count",
        )


class CompanySearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "slug",
            "industry",
            "city",
            "headquarters_location",
            "is_active",
            "created_at",
        )


class CollegeSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = (
            "id",
            "name",
            "slug",
            "city",
            "state",
            "country",
            "profile_status",
            "is_active",
            "created_at",
        )


class ApplicationSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    domain = serializers.CharField()
    status = serializers.CharField()
    applicant_name = serializers.CharField()
    title_snapshot = serializers.CharField()
    organization_snapshot = serializers.CharField()
    applied_at = serializers.DateTimeField()

    def to_representation(self, instance):
        if isinstance(instance, JobApplication):
            return {
                "id": str(instance.pk),
                "domain": "it",
                "status": instance.status,
                "applicant_name": instance.applicant_name_snapshot,
                "title_snapshot": instance.job_title_snapshot,
                "organization_snapshot": instance.company_name_snapshot,
                "applied_at": instance.applied_at,
            }
        if isinstance(instance, FacultyApplication):
            return {
                "id": str(instance.pk),
                "domain": "faculty",
                "status": instance.status,
                "applicant_name": instance.applicant_name_snapshot,
                "title_snapshot": instance.vacancy_title_snapshot,
                "organization_snapshot": instance.college_name_snapshot,
                "applied_at": instance.applied_at,
            }
        return super().to_representation(instance)


class InvoiceSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "invoice_number",
            "domain",
            "status",
            "total_amount",
            "amount_paid",
            "currency",
            "issued_at",
            "due_at",
            "bill_to_name_snapshot",
        )


class GuaranteeSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuaranteeClaim
        fields = (
            "id",
            "claim_number",
            "domain",
            "status",
            "claim_type",
            "reason",
            "submitted_at",
        )


class JobSeekerSearchResultSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = JobSeekerProfile
        fields = (
            "id",
            "full_name",
            "headline",
            "experience_years",
            "current_location",
            "profile_status",
            "profile_completeness",
            "email",
            "phone",
        )

    def get_full_name(self, obj) -> str:
        return obj.full_name

    def get_email(self, obj) -> str:
        from apps.it_recruitment.services.jobseeker_privacy_service import (
            JobSeekerPrivacyService,
        )

        viewer = self.context.get("viewer")
        return JobSeekerPrivacyService().contact_fields_for_viewer(obj, viewer)["email"]

    def get_phone(self, obj) -> str:
        from apps.it_recruitment.services.jobseeker_privacy_service import (
            JobSeekerPrivacyService,
        )

        viewer = self.context.get("viewer")
        return JobSeekerPrivacyService().contact_fields_for_viewer(obj, viewer)["phone"]


class RecruiterSearchResultSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = RecruiterProfile
        fields = (
            "id",
            "full_name",
            "department",
            "company_association",
            "designation",
            "profile_status",
        )

    def get_full_name(self, obj) -> str:
        return obj.full_name


class ProfessorSearchResultSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = ProfessorProfile
        fields = (
            "id",
            "full_name",
            "specialization",
            "current_designation",
            "current_institution",
            "experience_years",
            "profile_status",
        )

    def get_full_name(self, obj) -> str:
        return obj.full_name
