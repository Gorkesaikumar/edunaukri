from apps.core.repositories.crud import CRUDRepository, ReadRepository
from apps.applications.models import (
    FacultyApplication,
    FacultyApplicationTimelineEvent,
    JobApplication,
    JobApplicationTimelineEvent,
)


class ApplicationReadRepository(ReadRepository):
    model = JobApplication


class FacultyApplicationReadRepository(ReadRepository):
    model = FacultyApplication


class JobApplicationRepository(CRUDRepository):
    model = JobApplication
    search_fields = (
        "applicant_name_snapshot",
        "job_title_snapshot",
        "company_name_snapshot",
        "current_location",
    )


class FacultyApplicationRepository(CRUDRepository):
    model = FacultyApplication
    search_fields = (
        "applicant_name_snapshot",
        "vacancy_title_snapshot",
        "college_name_snapshot",
        "department",
        "current_institution",
    )


class JobApplicationTimelineRepository(CRUDRepository):
    model = JobApplicationTimelineEvent


class FacultyApplicationTimelineRepository(CRUDRepository):
    model = FacultyApplicationTimelineEvent
