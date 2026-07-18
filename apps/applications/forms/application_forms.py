"""Django forms for application admin flows."""

from django import forms

from apps.applications.models import FacultyApplication, JobApplication


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = (
            "job_posting",
            "job_seeker",
            "company",
            "status",
            "cover_letter",
            "expected_salary",
            "notice_period",
            "current_location",
            "source",
            "recruiter_notes",
            "candidate_notes",
            "internal_remarks",
        )


class FacultyApplicationForm(forms.ModelForm):
    class Meta:
        model = FacultyApplication
        fields = (
            "vacancy",
            "professor",
            "college",
            "status",
            "cover_letter",
            "department",
            "expected_salary",
            "current_institution",
            "current_designation",
            "research_publications_count",
            "source",
            "college_notes",
            "professor_notes",
            "internal_remarks",
        )
