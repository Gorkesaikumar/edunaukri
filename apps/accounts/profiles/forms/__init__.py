from apps.accounts.profiles.forms.college_profile_form import CollegeProfileForm
from apps.accounts.profiles.forms.job_seeker_profile_form import JobSeekerProfileForm
from apps.accounts.profiles.forms.professor_profile_form import ProfessorProfileForm
from apps.accounts.profiles.forms.recruiter_profile_form import RecruiterProfileForm

from apps.accounts.profiles.forms.registry import PROFILE_FORM_MAP, get_profile_form

__all__ = [
    "JobSeekerProfileForm",
    "RecruiterProfileForm",
    "ProfessorProfileForm",
    "CollegeProfileForm",
    "PROFILE_FORM_MAP",
    "get_profile_form",
]
