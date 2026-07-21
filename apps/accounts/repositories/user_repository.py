from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.faculty_user import FacultyUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.core.exceptions.domain_exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from apps.core.repositories.crud import FilteringRepository
from apps.core.utils.strings import normalize_email


DOMAIN_USER_MODELS = {
    "admin": AdminUser,
    "it": ITUser,
    "professor": ProfessorUser,
    "college": CollegeUser,
    "faculty": FacultyUser,
}


class DomainUserRepository(FilteringRepository):
    def __init__(self, model):
        self.model = model

    def get_by_email(self, email: str):
        return self.filter_by(email__iexact=normalize_email(email)).first()

    def get_by_id(self, user_id):
        try:
            return super().get_by_id(user_id)
        except ResourceNotFoundException:
            return None


def get_user_repository(domain: str) -> DomainUserRepository:
    model = DOMAIN_USER_MODELS.get(domain)
    if not model:
        raise ValidationException("Invalid domain.")
    return DomainUserRepository(model)
