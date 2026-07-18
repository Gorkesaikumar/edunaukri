"""Django forms for faculty vacancy management (admin site / server-rendered flows)."""

from django import forms

from apps.faculty.models import FacultyVacancy, FacultyVacancyCampus
from apps.faculty.validators.vacancy_validators import (
    validate_experience_range,
    validate_salary_range,
    validate_vacancy_count,
)


class FacultyVacancyForm(forms.ModelForm):
    class Meta:
        model = FacultyVacancy
        fields = (
            "college",
            "posted_by",
            "title",
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
            "expires_at",
        )

    def clean_vacancy_count(self):
        value = self.cleaned_data.get("vacancy_count")
        validate_vacancy_count(value)
        return value

    def clean(self):
        cleaned = super().clean()
        validate_salary_range(cleaned.get("salary_min"), cleaned.get("salary_max"))
        validate_experience_range(
            cleaned.get("experience_min"), cleaned.get("experience_max")
        )
        return cleaned


class FacultyVacancyCampusForm(forms.ModelForm):
    class Meta:
        model = FacultyVacancyCampus
        fields = (
            "vacancy",
            "country",
            "state",
            "district",
            "city",
            "campus",
            "work_type",
            "is_primary",
        )
