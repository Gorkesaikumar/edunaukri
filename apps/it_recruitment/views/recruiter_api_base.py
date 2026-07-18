"""Shared base for recruiter portal JSON APIs under /recruiter/<uuid>/... routes."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View


class RecruiterScopedAPIView(LoginRequiredMixin, View):
    """Strip URL-scoped user_uuid before handler dispatch."""

    login_url = "/it/login/recruiter/"

    def dispatch(self, request, *args, **kwargs):
        kwargs.pop("user_uuid", None)
        return super().dispatch(request, *args, **kwargs)
