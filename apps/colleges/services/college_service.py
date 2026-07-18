from apps.colleges.models import College
from apps.colleges.services.institution_service import InstitutionService
from apps.core.services.base import BaseService


class CollegeService(BaseService):
    """Backward-compatible facade over :class:`InstitutionService`.

    The academic profile flow (``/api/v1/faculty/colleges/``) creates colleges
    through ``ProfileService`` which calls ``create_college`` here. The full
    Institution Management module lives in :class:`InstitutionService`.
    """

    def __init__(self):
        self.institution_service = InstitutionService()

    @BaseService.atomic
    def create_college(self, *, college_user, data: dict) -> College:
        return self.institution_service.create_institution(
            college_user=college_user, data=data
        )
