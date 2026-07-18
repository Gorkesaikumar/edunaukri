from apps.academic_recruitment.models.account_settings import (
    CollegeAccountSettings,
    ProfessorAccountSettings,
)
from apps.academic_recruitment.models.professor import (
    ProfessorCertification,
    ProfessorDepartment,
    ProfessorProfile,
    ProfessorQualification,
    Qualification,
)
from apps.academic_recruitment.models.resume import ParsedResume

__all__ = [
    "ProfessorProfile",
    "Qualification",
    "ProfessorQualification",
    "ProfessorDepartment",
    "ProfessorCertification",
    "ParsedResume",
    "ProfessorAccountSettings",
    "CollegeAccountSettings",
]
