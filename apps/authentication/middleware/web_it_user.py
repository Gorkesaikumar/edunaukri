"""Hydrate request.user from JWT cookies when the Django session is absent."""

from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.authentication.services.session_service import BACKEND_MAP
from apps.authentication.services.web_jwt_service import WebJWTService


class WebITUserMiddleware:
    """Ensure web-domain users authenticated via HttpOnly JWT cookies are visible to views."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if not (
            user
            and user.is_authenticated
            and isinstance(user, (ITUser, ProfessorUser, CollegeUser))
        ):
            web_user = WebJWTService.get_valid_web_user(request)
            if web_user is not None:
                domain = WebJWTService._domain_for_user(web_user)
                if domain in BACKEND_MAP:
                    web_user.backend = BACKEND_MAP[domain]
                request.user = web_user
        return self.get_response(request)
