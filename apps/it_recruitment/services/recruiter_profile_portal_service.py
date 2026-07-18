"""Recruiter company profile portal — recruiter + primary company context."""

from __future__ import annotations

from dataclasses import dataclass

from apps.authentication.services.portal_url_service import PortalURLService
from apps.companies.constants.enums import CompanyMemberRole
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile
from apps.it_recruitment.services.jobseeker_portal_helpers import (
    initials_from_name,
    media_url,
)


@dataclass
class RecruiterProfilePortalContext:
    recruiter: dict
    company: dict | None
    has_company: bool
    api_urls: dict


class RecruiterProfilePortalService(BaseService):
    def build(self, profile: RecruiterProfile) -> RecruiterProfilePortalContext:
        user = profile.user
        pu = lambda name, **kw: PortalURLService.recruiter(user, name, **kw)
        company = self._primary_company(profile)
        return RecruiterProfilePortalContext(
            recruiter=self._serialize_recruiter(profile),
            company=company,
            has_company=company is not None,
            api_urls={
                "profile": pu("recruiter_profile_api"),
                "company": pu("recruiter_company_api"),
                "create_company": pu("recruiter_company_create_api"),
            },
        )

    @staticmethod
    def _serialize_recruiter(profile: RecruiterProfile) -> dict:
        return {
            "id": str(profile.pk),
            "full_name": profile.full_name,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "phone": profile.phone,
            "official_email": profile.official_email,
            "designation": profile.designation,
            "department": profile.department,
            "company_association": profile.company_association,
            "initials": initials_from_name(profile.full_name, profile.user.email[:2]),
            "avatar_url": media_url(profile.profile_image)
            if profile.profile_image
            else None,
            "login_email": profile.user.email,
        }

    @staticmethod
    def _primary_company(profile: RecruiterProfile) -> dict | None:
        membership = (
            CompanyMemberSelector()
            .for_recruiter(profile)
            .select_related("company")
            .order_by("-is_primary", "-created_at")
            .first()
        )
        if not membership:
            return None
        company = membership.company

        logo_url = None
        if company.logo_file and getattr(company.logo_file, "storage_path", None):
            logo_url = media_url(company.logo_file)
        return {
            "id": str(company.pk),
            "name": company.name,
            "legal_name": company.legal_name,
            "industry": company.industry,
            "description": company.description,
            "website_url": company.website_url,
            "email": company.email,
            "phone": company.phone,
            "headquarters_location": company.headquarters_location,
            "city": company.city,
            "state": company.state,
            "country": company.country or "India",
            "verification_status": "VERIFIED" if company.is_verified else "PENDING",
            "verification_label": "Verified" if company.is_verified else "Pending",
            "is_verified": company.is_verified,
            "verified_at": None,
            "can_publish_jobs": company.can_publish_jobs,
            "is_active": company.is_active,
            "logo_url": logo_url,
            "member_role": membership.role,
            "is_owner": membership.role == CompanyMemberRole.OWNER,
        }
