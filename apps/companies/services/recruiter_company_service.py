"""Recruiter-facing company creation and profile orchestration."""

from __future__ import annotations

from apps.companies.models import Company
from apps.companies.services.company_service import CompanyService
from apps.core.exceptions.domain_exceptions import (
    BusinessLogicException,
    ConflictException,
)
from apps.core.services.base import BaseService
from apps.it_recruitment.models import RecruiterProfile


class RecruiterCompanyService(BaseService):
    """Create and manage companies on behalf of authenticated recruiters."""

    def __init__(self):
        self._companies = CompanyService()

    @BaseService.atomic
    def create_company(self, *, recruiter: RecruiterProfile, data: dict) -> Company:
        name = (data.get("name") or "").strip()
        if not name:
            raise BusinessLogicException("Company name is required.")

        company = self._companies.create_company(recruiter=recruiter, data=data)
        return company

    @BaseService.atomic
    def update_company(
        self, *, company: Company, recruiter: RecruiterProfile, data: dict
    ) -> Company:
        company = self._companies.update_company(
            company=company, recruiter=recruiter, data=data
        )
        return company

    @staticmethod
    def friendly_error(exc: Exception) -> str:
        message = str(exc)
        if isinstance(exc, ConflictException):
            if "slug" in message.lower():
                return "A company with this name already exists."
            if "already belongs" in message.lower():
                return "You already have a company profile linked to your account."
        return message
