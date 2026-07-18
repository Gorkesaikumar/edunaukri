from django import forms

from apps.accounts.profiles.constants.enums import ProfileType, ProfileVisibility
from apps.accounts.profiles.forms.base import BaseProfileForm


class RecruiterProfileForm(BaseProfileForm):
    profile_type = ProfileType.RECRUITER

    first_name = forms.CharField(max_length=100)
    last_name = forms.CharField(max_length=100)
    phone = forms.CharField(max_length=20, required=False)
    official_email = forms.EmailField(required=False)
    designation = forms.CharField(max_length=150, required=False)
    department = forms.CharField(max_length=150, required=False)
    company_association = forms.CharField(max_length=300, required=False)
    profile_image_id = forms.UUIDField(required=False)
    profile_visibility = forms.ChoiceField(
        choices=ProfileVisibility.choices, required=False
    )
