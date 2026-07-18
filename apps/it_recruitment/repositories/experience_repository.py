"""Repositories for job seeker profile nested records."""

from apps.core.repositories.crud import CRUDRepository
from apps.it_recruitment.models import (
    JobSeekerCertification,
    JobSeekerEducation,
    JobSeekerExperience,
    JobSeekerProject,
)


class JobSeekerExperienceRepository(CRUDRepository):
    model = JobSeekerExperience


class JobSeekerEducationRepository(CRUDRepository):
    model = JobSeekerEducation


class JobSeekerProjectRepository(CRUDRepository):
    model = JobSeekerProject


class JobSeekerCertificationRepository(CRUDRepository):
    model = JobSeekerCertification
