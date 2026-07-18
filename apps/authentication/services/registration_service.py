from django.db import transaction

from apps.accounts.constants.enums import AccountStatus, ITUserRoleType
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.services.role_assignment_service import RoleAssignmentService
from apps.authentication.validators.password_validator import validate_password_strength
from apps.core.services.base import BaseService


class RegistrationService(BaseService):
    @transaction.atomic
    def register_job_seeker(self, *, email: str, password: str) -> ITUser:
        user = self._register(ITUser, email=email, password=password)
        RoleAssignmentService().assign_it_role(
            user=user, role=ITUserRoleType.JOB_SEEKER
        )
        return user

    @transaction.atomic
    def register_recruiter(self, *, email: str, password: str) -> ITUser:
        user = self._register(ITUser, email=email, password=password)
        RoleAssignmentService().assign_it_role(user=user, role=ITUserRoleType.RECRUITER)
        return user

    @transaction.atomic
    def register_it_user(self, *, email: str, password: str) -> ITUser:
        """Legacy generic IT registration — no role until profile creation."""
        return self._register(ITUser, email=email, password=password)

    @transaction.atomic
    def register_professor(self, *, email: str, password: str) -> ProfessorUser:
        return self._register(ProfessorUser, email=email, password=password)

    @transaction.atomic
    def register_college_user(self, *, email: str, password: str) -> CollegeUser:
        return self._register(CollegeUser, email=email, password=password)

    def _register(self, model, *, email: str, password: str):
        from django.core.exceptions import ValidationError

        email = email.lower().strip()
        if model.objects.filter(email=email, is_deleted=False).exists():
            raise ValidationError("An account with this email already exists.")
        validate_password_strength(password)
        user = model(email=email, account_status=AccountStatus.PENDING_VERIFICATION)
        user.set_password(password)
        user.save()
        return user
