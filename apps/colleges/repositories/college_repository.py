from apps.accounts.profiles.repositories.base import (
    ProfileRepository,
    ReadOnlyProfileRepository,
)
from apps.colleges.models import (
    College,
    CollegeDepartment,
    CollegeMember,
    Department,
    InstitutionCampus,
    InstitutionDocument,
)
from apps.core.repositories.crud import CRUDRepository


class CollegeReadRepository(ReadOnlyProfileRepository):
    model = College


class InstitutionReadRepository(CollegeReadRepository):
    """Read-only institution repository (alias exposed by the institution module)."""


class CollegeRepository(ProfileRepository):
    model = College
    search_fields = ("name", "legal_name", "city", "district", "state")


class InstitutionRepository(CollegeRepository):
    """Write-side institution repository (alias exposed by the institution module)."""


class CollegeMemberRepository(CRUDRepository):
    model = CollegeMember


class DepartmentRepository(CRUDRepository):
    model = Department
    search_fields = ("name", "category")


class CollegeDepartmentRepository(CRUDRepository):
    model = CollegeDepartment


class InstitutionCampusRepository(CRUDRepository):
    model = InstitutionCampus


class InstitutionDocumentRepository(CRUDRepository):
    model = InstitutionDocument
