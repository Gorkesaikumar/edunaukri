from apps.accounts.profiles.constants.enums import ProfileType
from apps.core.services.base import BaseService


def _filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


class ProfileCompletionService(BaseService):
    """Calculate profile completion percentage per role."""

    def calculate(self, profile, profile_type: ProfileType) -> int:
        calculators = {
            ProfileType.JOB_SEEKER: self._job_seeker,
            ProfileType.RECRUITER: self._recruiter,
            ProfileType.PROFESSOR: self._professor,
            ProfileType.COLLEGE: self._college,
        }
        calculator = calculators.get(profile_type)
        if not calculator:
            return 100
        return min(100, max(0, calculator(profile)))

    def _score(self, checks: list[tuple[int, bool]]) -> int:
        total_weight = sum(weight for weight, _ in checks)
        if total_weight == 0:
            return 0
        earned = sum(weight for weight, ok in checks if ok)
        return round((earned / total_weight) * 100)

    def _job_seeker(self, profile) -> int:
        has_skills = profile.skills.filter(is_deleted=False).exists()
        has_experience = profile.experiences.filter(is_deleted=False).exists()
        has_education = profile.education.filter(is_deleted=False).exists()
        has_social = (
            _filled(profile.linkedin_url)
            or _filled(profile.github_url)
            or _filled(profile.portfolio_url)
        )
        checks = [
            (5, _filled(profile.first_name)),
            (5, _filled(profile.last_name)),
            (5, _filled(profile.phone)),
            (5, _filled(profile.headline)),
            (10, _filled(profile.summary)),
            (5, profile.experience_years is not None),
            (
                5,
                _filled(profile.current_location)
                or _filled(profile.preferred_location),
            ),
            (5, profile.expected_salary is not None),
            (5, profile.resume_file_id is not None),
            (5, profile.profile_photo_id is not None),
            (10, has_skills),
            (10, has_experience),
            (10, has_education),
            (10, has_social),
            (5, _filled(profile.languages)),
            (5, _filled(profile.current_company)),
        ]
        return self._score(checks)

    def _recruiter(self, profile) -> int:
        checks = [
            (10, _filled(profile.first_name)),
            (10, _filled(profile.last_name)),
            (10, _filled(profile.phone)),
            (15, _filled(profile.designation)),
            (10, _filled(profile.department)),
            (15, _filled(profile.official_email)),
            (10, _filled(profile.company_association)),
            (10, profile.profile_image_id is not None),
            (10, _filled(profile.profile_visibility)),
        ]
        return self._score(checks)

    def _professor(self, profile) -> int:
        has_qualifications = profile.qualifications.filter(is_deleted=False).exists()
        has_departments = profile.departments.filter(is_deleted=False).exists()
        has_certifications = (
            profile.certifications.filter(is_deleted=False).exists()
            if hasattr(profile, "certifications")
            else False
        )
        has_experience = (
            profile.teaching_experience_years is not None
            or profile.industry_experience_years is not None
            or profile.experience_years is not None
        )
        has_social = (
            _filled(getattr(profile, "linkedin_url", None))
            or _filled(getattr(profile, "google_scholar_url", None))
            or _filled(getattr(profile, "website_url", None))
            or (profile.publications_count > 0)
        )
        has_languages = _filled(getattr(profile, "languages", None)) or bool(
            profile.preferred_locations
        )
        checks = [
            (
                10,
                _filled(profile.first_name)
                and _filled(profile.last_name)
                and _filled(profile.phone),
            ),
            (10, has_qualifications or _filled(profile.highest_qualification)),
            (10, has_experience or _filled(profile.current_designation)),
            (
                10,
                _filled(profile.specialization) and _filled(profile.research_interests),
            ),
            (15, profile.cv_file_id is not None),
            (
                10,
                has_certifications
                or profile.qualifications.filter(
                    is_deleted=False, certificate_file__isnull=False
                ).exists(),
            ),
            (10, profile.profile_photo_id is not None),
            (10, bool(profile.preferred_locations)),
            (5, has_languages),
            (10, has_social),
        ]
        return self._score(checks)

    def _college(self, profile) -> int:
        has_departments = profile.departments.filter(is_deleted=False).exists()
        checks = [
            (10, _filled(profile.name)),
            (5, _filled(profile.college_type)),
            (5, _filled(profile.address_line)),
            (5, _filled(profile.city)),
            (5, _filled(profile.state)),
            (10, _filled(profile.website_url)),
            (5, _filled(profile.contact_phone)),
            (5, _filled(profile.contact_email)),
            (10, _filled(profile.aicte_code) or _filled(profile.ugc_code)),
            (10, _filled(profile.naac_grade)),
            (15, profile.logo_file_id is not None),
            (10, has_departments),
            (5, _filled(profile.description)),
        ]
        return self._score(checks)
