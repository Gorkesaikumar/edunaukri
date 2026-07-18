from apps.accounts.profiles.constants.enums import ProfileType
from apps.accounts.profiles.forms.college_profile_form import CollegeProfileForm
from apps.accounts.profiles.forms.job_seeker_profile_form import JobSeekerProfileForm
from apps.accounts.profiles.forms.professor_profile_form import ProfessorProfileForm
from apps.accounts.profiles.forms.recruiter_profile_form import RecruiterProfileForm

PROFILE_FORM_MAP = {
    ProfileType.JOB_SEEKER: JobSeekerProfileForm,
    ProfileType.RECRUITER: RecruiterProfileForm,
    ProfileType.PROFESSOR: ProfessorProfileForm,
    ProfileType.COLLEGE: CollegeProfileForm,
}


def get_profile_form(
    profile_type: ProfileType, data: dict | None = None, *, is_create: bool = True
):
    form_class = PROFILE_FORM_MAP.get(profile_type)
    if not form_class:
        raise ValueError(f"No profile form registered for {profile_type}.")
    return form_class(data=data or {}, is_create=is_create)
