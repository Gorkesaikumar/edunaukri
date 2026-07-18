from django import forms

from apps.accounts.profiles.constants.enums import ProfileType, ProfileVisibility
from apps.accounts.profiles.forms.base import BaseProfileForm


class ProfessorProfileForm(BaseProfileForm):
    profile_type = ProfileType.PROFESSOR

    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20, required=False)
    highest_qualification = forms.CharField(max_length=200, required=False)
    specialization = forms.CharField(max_length=200, required=False)
    research_interests = forms.CharField(required=False, widget=forms.Textarea)
    experience_years = forms.IntegerField(required=False, min_value=0, max_value=60)
    teaching_experience_years = forms.IntegerField(
        required=False, min_value=0, max_value=60
    )
    industry_experience_years = forms.IntegerField(
        required=False, min_value=0, max_value=60
    )
    publications_count = forms.IntegerField(required=False, min_value=0)
    current_designation = forms.CharField(max_length=150, required=False)
    current_institution = forms.CharField(max_length=300, required=False)
    expected_salary = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2
    )
    preferred_locations = forms.JSONField(required=False)
    profile_photo_id = forms.UUIDField(required=False)
    cv_file_id = forms.UUIDField(required=False)
    profile_visibility = forms.ChoiceField(
        choices=ProfileVisibility.choices, required=False
    )
    department_ids = forms.JSONField(required=False)
    qualifications = forms.JSONField(required=False)
