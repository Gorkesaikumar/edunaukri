"""Shared base for institution portal JSON APIs under /college/<uuid>/... routes."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View


class CollegeScopedAPIView(LoginRequiredMixin, View):
    """Strip URL-scoped user_uuid before handler dispatch."""

    login_url = "/faculty/login/institution/"

    def dispatch(self, request, *args, **kwargs):
        kwargs.pop("user_uuid", None)
        return super().dispatch(request, *args, **kwargs)
