"""Django forms for company management (admin site / server-rendered flows)."""

from django import forms

from apps.companies.models import Company, CompanyLocation
from apps.companies.validators.company_validators import (
    validate_company_phone,
    validate_founded_year,
    validate_gst_number,
    validate_social_link,
)


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "name",
            "legal_name",
            "description",
            "mission",
            "vision",
            "benefits",
            "culture",
            "industry",
            "organization_type",
            "company_size",
            "founded_year",
            "gst_number",
            "website_url",
            "email",
            "phone",
            "headquarters_location",
            "address_line",
            "city",
            "state",
            "country",
            "postal_code",
            "linkedin_url",
            "twitter_url",
            "facebook_url",
            "instagram_url",
            "youtube_url",
        )

    def clean_gst_number(self):
        value = self.cleaned_data.get("gst_number", "")
        if value:
            validate_gst_number(value)
        return value

    def clean_phone(self):
        value = self.cleaned_data.get("phone", "")
        if value:
            validate_company_phone(value)
        return value

    def clean_founded_year(self):
        value = self.cleaned_data.get("founded_year")
        validate_founded_year(value)
        return value

    def _clean_social(self, field):
        value = self.cleaned_data.get(field, "")
        if value:
            validate_social_link(value, field=field)
        return value

    def clean_linkedin_url(self):
        return self._clean_social("linkedin_url")

    def clean_twitter_url(self):
        return self._clean_social("twitter_url")

    def clean_facebook_url(self):
        return self._clean_social("facebook_url")

    def clean_instagram_url(self):
        return self._clean_social("instagram_url")

    def clean_youtube_url(self):
        return self._clean_social("youtube_url")


class CompanyLocationForm(forms.ModelForm):
    class Meta:
        model = CompanyLocation
        fields = (
            "company",
            "label",
            "address_line",
            "city",
            "state",
            "country",
            "postal_code",
            "is_headquarters",
        )
