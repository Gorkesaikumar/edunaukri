from apps.authentication.models import LoginAttempt
from apps.core.repositories.crud import CRUDRepository


class LoginAttemptRepository(CRUDRepository):
    model = LoginAttempt
