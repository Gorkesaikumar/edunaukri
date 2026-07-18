from django import forms

from apps.accounts.profiles.constants.enums import (
    EmploymentTypePreference,
    Gender,
    ProfileType,
    ProfileVisibility,
    WorkModePreference,
)
from apps.accounts.profiles.forms.base import BaseProfileForm


class JobSeekerProfileForm(BaseProfileForm):
    profile_type = ProfileType.JOB_SEEKER

    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20, required=False)
    gender = forms.ChoiceField(choices=Gender.choices, required=False)
    date_of_birth = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    country = forms.CharField(max_length=100, required=False)
    headline = forms.CharField(max_length=300, required=False)
    summary = forms.CharField(required=False, widget=forms.Textarea)
    experience_years = forms.IntegerField(required=False, min_value=0, max_value=60)
    current_location = forms.CharField(max_length=200, required=False)
    preferred_location = forms.CharField(max_length=200, required=False)
    current_company = forms.CharField(max_length=200, required=False)
    current_salary = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2
    )
    expected_salary = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2
    )
    notice_period_days = forms.IntegerField(required=False, min_value=0, max_value=365)
    employment_type_preference = forms.ChoiceField(
        choices=EmploymentTypePreference.choices, required=False
    )
    work_mode_preference = forms.ChoiceField(
        choices=WorkModePreference.choices, required=False
    )
    preferred_roles = forms.JSONField(required=False)
    personal_website = forms.URLField(required=False, assume_scheme="https")
    linkedin_url = forms.URLField(required=False, assume_scheme="https")
    github_url = forms.URLField(required=False, assume_scheme="https")
    portfolio_url = forms.URLField(required=False, assume_scheme="https")
    languages = forms.JSONField(required=False)
    profile_photo_id = forms.UUIDField(required=False)
    resume_file_id = forms.UUIDField(required=False)
    profile_visibility = forms.ChoiceField(
        choices=ProfileVisibility.choices, required=False
    )
    skills = forms.JSONField(required=False)
    experiences = forms.JSONField(required=False)
    education = forms.JSONField(required=False)
    projects = forms.JSONField(required=False)
    certifications = forms.JSONField(required=False)
