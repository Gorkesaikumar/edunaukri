from django import forms

from apps.accounts.profiles.constants.enums import ProfileType, ProfileVisibility
from apps.accounts.profiles.forms.base import BaseProfileForm


class CollegeProfileForm(BaseProfileForm):
    profile_type = ProfileType.COLLEGE

    name = forms.CharField(max_length=300)
    college_type = forms.CharField(max_length=50, required=False)
    description = forms.CharField(required=False, widget=forms.Textarea)
    website_url = forms.URLField(required=False, assume_scheme="https")
    address_line = forms.CharField(max_length=500, required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    pin_code = forms.CharField(max_length=10, required=False)
    accreditation = forms.CharField(max_length=100, required=False)
    aicte_code = forms.CharField(max_length=100, required=False)
    ugc_code = forms.CharField(max_length=100, required=False)
    naac_grade = forms.CharField(max_length=10, required=False)
    contact_phone = forms.CharField(max_length=20, required=False)
    contact_email = forms.EmailField(required=False)
    established_year = forms.IntegerField(
        required=False, min_value=1800, max_value=2100
    )
    logo_file_id = forms.UUIDField(required=False)
    profile_visibility = forms.ChoiceField(
        choices=ProfileVisibility.choices, required=False
    )
    department_ids = forms.JSONField(required=False)
