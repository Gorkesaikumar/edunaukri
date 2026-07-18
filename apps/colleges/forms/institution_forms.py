"""Django forms for institution management (admin site / server-rendered flows)."""

from django import forms

from apps.colleges.models import College, InstitutionCampus
from apps.colleges.validators.college_validators import (
    validate_accreditation_number,
    validate_established_year,
    validate_institution_phone,
    validate_postal_code,
    validate_social_link,
)


class InstitutionForm(forms.ModelForm):
    class Meta:
        model = College
        fields = (
            "name",
            "legal_name",
            "college_type",
            "institution_type",
            "ownership_type",
            "autonomous_status",
            "description",
            "vision",
            "mission",
            "infrastructure_description",
            "facilities",
            "placement_cell_details",
            "research_centers",
            "hostel_availability",
            "transportation_facilities",
            "affiliated_university",
            "academic_calendar_reference",
            "accreditation",
            "aicte_code",
            "ugc_code",
            "naac_grade",
            "nba_accreditation",
            "established_year",
            "campus_area",
            "number_of_students",
            "number_of_faculty",
            "website_url",
            "contact_email",
            "contact_phone",
            "alternate_phone",
            "address_line",
            "city",
            "district",
            "state",
            "country",
            "pin_code",
            "latitude",
            "longitude",
            "linkedin_url",
            "facebook_url",
            "instagram_url",
            "twitter_url",
            "youtube_url",
        )

    def clean_pin_code(self):
        value = self.cleaned_data.get("pin_code", "")
        validate_postal_code(value)
        return value

    def clean_contact_phone(self):
        value = self.cleaned_data.get("contact_phone", "")
        if value:
            validate_institution_phone(value)
        return value

    def clean_established_year(self):
        value = self.cleaned_data.get("established_year")
        validate_established_year(value)
        return value

    def clean_aicte_code(self):
        value = self.cleaned_data.get("aicte_code", "")
        validate_accreditation_number(value, label="AICTE approval number")
        return value

    def clean_ugc_code(self):
        value = self.cleaned_data.get("ugc_code", "")
        validate_accreditation_number(value, label="UGC recognition number")
        return value

    def _clean_social(self, field):
        value = self.cleaned_data.get(field, "")
        if value:
            validate_social_link(value, field=field)
        return value

    def clean_linkedin_url(self):
        return self._clean_social("linkedin_url")

    def clean_facebook_url(self):
        return self._clean_social("facebook_url")

    def clean_instagram_url(self):
        return self._clean_social("instagram_url")

    def clean_twitter_url(self):
        return self._clean_social("twitter_url")

    def clean_youtube_url(self):
        return self._clean_social("youtube_url")


class InstitutionCampusForm(forms.ModelForm):
    class Meta:
        model = InstitutionCampus
        fields = (
            "college",
            "label",
            "address_line",
            "city",
            "district",
            "state",
            "country",
            "pin_code",
            "latitude",
            "longitude",
            "is_main_campus",
        )
