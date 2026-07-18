from apps.colleges.services.college_service import CollegeService
from apps.colleges.services.department_management_service import (
    DepartmentManagementService,
)
from apps.colleges.services.institution_branding_service import (
    InstitutionBrandingService,
)
from apps.colleges.services.institution_campus_service import InstitutionCampusService
from apps.colleges.services.institution_document_service import (
    InstitutionDocumentService,
)
from apps.colleges.services.institution_member_service import InstitutionMemberService
from apps.colleges.services.institution_service import InstitutionService
from apps.colleges.services.institution_statistics_service import (
    InstitutionStatisticsService,
)

__all__ = [
    "CollegeService",
    "InstitutionService",
    "InstitutionBrandingService",
    "InstitutionStatisticsService",
    "DepartmentManagementService",
    "InstitutionMemberService",
    "InstitutionCampusService",
    "InstitutionDocumentService",
]
