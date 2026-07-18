"""Django forms for job management (admin site / server-rendered flows)."""

from django import forms

from apps.jobs.models import JobLocation, JobPosting
from apps.jobs.validators.job_validators import (
    validate_experience_range,
    validate_salary_range,
    validate_vacancies,
)


class JobPostingForm(forms.ModelForm):
    class Meta:
        model = JobPosting
        fields = (
            "company",
            "posted_by",
            "title",
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
            "expires_at",
        )

    def clean_vacancies(self):
        value = self.cleaned_data.get("vacancies")
        validate_vacancies(value)
        return value

    def clean(self):
        cleaned = super().clean()
        validate_salary_range(cleaned.get("salary_min"), cleaned.get("salary_max"))
        validate_experience_range(
            cleaned.get("experience_min"), cleaned.get("experience_max")
        )
        return cleaned


class JobLocationForm(forms.ModelForm):
    class Meta:
        model = JobLocation
        fields = (
            "job_posting",
            "country",
            "state",
            "city",
            "office_address",
            "work_mode",
            "is_primary",
        )
