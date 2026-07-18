from apps.companies.models import Company, CompanyLocation, CompanyMember
from apps.core.repositories.crud import CRUDRepository, ReadRepository


class CompanyRepository(CRUDRepository):
    """Write-side repository for companies."""

    model = Company
    search_fields = ("name", "legal_name", "industry", "headquarters_location", "city")


class CompanyReadRepository(ReadRepository):
    """Read-only repository for companies (queries never mutate state)."""

    model = Company


class CompanyMemberRepository(CRUDRepository):
    model = CompanyMember


class CompanyLocationRepository(CRUDRepository):
    model = CompanyLocation
