from apps.applications.models import (
    FacultyApplicationStatusHistory,
    JobApplicationStatusHistory,
)
from apps.core.repositories.crud import CRUDRepository


class JobApplicationStatusHistoryRepository(CRUDRepository):
    model = JobApplicationStatusHistory


class FacultyApplicationStatusHistoryRepository(CRUDRepository):
    model = FacultyApplicationStatusHistory
