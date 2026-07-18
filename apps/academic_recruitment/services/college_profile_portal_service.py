"""Institution profile portal — read and manage primary institution."""

from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.models.college_user import CollegeUser
from apps.authentication.services.portal_url_service import PortalURLService
from apps.colleges.constants.enums import CollegeMemberRole
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.services.jobseeker_portal_helpers import media_url


@dataclass
class CollegeProfilePortalContext:
    institution: dict | None
    has_institution: bool
    member_role: str
    is_owner: bool
    verification_checklist: list[dict]
    profile_completion: int
    profile_completion_state: dict | None
    api_urls: dict


class CollegeProfilePortalService(BaseService):
    def build(self, user: CollegeUser) -> CollegeProfilePortalContext:
        pu = lambda name, **kw: PortalURLService.college(user, name, **kw)
        membership = (
            CollegeMemberSelector()
            .for_user(user)
            .select_related("college", "college__logo_file")
            .order_by("-is_primary", "-created_at")
            .first()
        )
        institution = self._serialize_institution(membership) if membership else None
        checklist = (
            self._verification_checklist(membership.college) if membership else []
        )
        if membership:
            from apps.academic_recruitment.services.college_profile_completion_service import CollegeProfileCompletionService
            completion_state = CollegeProfileCompletionService().get_dashboard_state(membership.college, user)
            completion = completion_state.percentage
            completion_state_dict = completion_state.to_dict()
        else:
            completion = 0
            completion_state_dict = None

        return CollegeProfilePortalContext(
            institution=institution,
            has_institution=institution is not None,
            member_role=membership.role if membership else "",
            is_owner=membership.role == CollegeMemberRole.OWNER
            if membership
            else False,
            verification_checklist=checklist,
            profile_completion=completion,
            profile_completion_state=completion_state_dict,
            api_urls={
                "institution": pu("college_institution_api"),
            },
        )

    @staticmethod
    def _serialize_institution(membership) -> dict:
        college = membership.college
        logo_url = media_url(college.logo_file) if college.logo_file else None
        banner_url = (
            media_url(college.cover_banner_file) if college.cover_banner_file else None
        )

        # Backward-compatible mapping: `verification_status` was replaced by `profile_status`.
        verification_status = getattr(college, "verification_status", None) or getattr(
            college, "profile_status", ""
        )
        verification_label_getter = getattr(
            college, "get_verification_status_display", None
        )
        if callable(verification_label_getter):
            verification_label = verification_label_getter()
        else:
            profile_label_getter = getattr(college, "get_profile_status_display", None)
            if callable(profile_label_getter):
                verification_label = profile_label_getter()
            else:
                verification_label = str(verification_status).replace("_", " ").title()

        # Calculate some summary stats for the profile header
        from apps.faculty.models import FacultyVacancy
        from apps.applications.models import FacultyApplication
        from apps.faculty.constants.enums import VacancyStatus

        total_vacancies = FacultyVacancy.objects.filter(
            college=college, status=VacancyStatus.PUBLISHED
        ).count()
        total_applications = FacultyApplication.objects.filter(
            vacancy__college=college
        ).count()

        return {
            "id": str(college.pk),
            "name": college.name,
            "legal_name": college.legal_name,
            "slug": college.slug,
            "description": college.description,
            "vision": college.vision,
            "mission": college.mission,
            "institution_type": college.institution_type,
            "ownership_type": college.ownership_type,
            "city": college.city,
            "state": college.state,
            "country": college.country or "India",
            "address_line": college.address_line,
            "pin_code": college.pin_code,
            "contact_email": college.contact_email,
            "contact_phone": college.contact_phone,
            "website_url": college.website_url,
            "linkedin_url": college.linkedin_url,
            "facebook_url": college.facebook_url,
            "instagram_url": college.instagram_url,
            "twitter_url": college.twitter_url,
            "youtube_url": college.youtube_url,
            "verification_status": verification_status,
            "verification_label": verification_label,
            "is_verified": college.is_verified,
            "can_publish": college.can_publish_vacancies,
            "is_active": college.is_active,
            "logo_url": logo_url,
            "banner_url": banner_url,
            "established_year": college.established_year,
            "accreditation": college.accreditation,
            "naac_grade": college.naac_grade,
            "number_of_faculty": college.number_of_faculty,
            "number_of_students": college.number_of_students,
            "member_role": membership.role,
            "member_role_label": membership.get_role_display(),
            "updated_at": college.updated_at.isoformat()
            if college.updated_at
            else None,
            "stats": {"vacancies": total_vacancies, "applications": total_applications},
        }

    @staticmethod
    def _verification_checklist(college) -> list[dict]:
        items = [
            ("logo", "Institution Logo", bool(college.logo_file_id)),
            ("banner", "Cover Banner", bool(college.cover_banner_file_id)),
            ("description", "Description", bool((college.description or "").strip())),
            (
                "contact",
                "Contact Details",
                bool(college.contact_email and college.contact_phone),
            ),
            (
                "location",
                "Address & Location",
                bool(college.city and college.state and college.address_line),
            ),
            ("website", "Website URL", bool(college.website_url)),
            (
                "accreditation",
                "Accreditation (NAAC/NBA/UGC)",
                bool(college.accreditation or college.naac_grade or college.ugc_code),
            ),
            (
                "vision",
                "Vision & Mission",
                bool(
                    (college.vision or "").strip() and (college.mission or "").strip()
                ),
            ),
            (
                "stats",
                "Institution Statistics",
                bool(college.established_year and college.number_of_faculty),
            ),
            (
                "social",
                "Social Media Links",
                bool(
                    college.linkedin_url or college.twitter_url or college.facebook_url
                ),
            ),
        ]
        return [
            {"key": key, "label": label, "done": done} for key, label, done in items
        ]
