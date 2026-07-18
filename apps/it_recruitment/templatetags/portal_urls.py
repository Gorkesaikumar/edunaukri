"""Template helpers for UUID-scoped portal URLs."""

from __future__ import annotations

from django import template

from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService

register = template.Library()


@register.simple_tag(takes_context=True)
def portal_url(context, view_name, *args, **kwargs):
    """Reverse a portal URL with the authenticated user's UUID."""
    if args:
        if "application" in view_name or "claim" in view_name:
            kwargs.setdefault("application_id", args[0])
        elif "vacancy" in view_name:
            kwargs.setdefault("vacancy_id", args[0])
        elif "notification" in view_name:
            kwargs.setdefault("notification_id", args[0])
        elif "job" in view_name:
            kwargs.setdefault("job_id", args[0])

    request = context.get("request")
    user = None
    if request is not None:
        user = WebJWTService.get_valid_it_user(request)
        if (
            user is None
            and getattr(request, "user", None)
            and request.user.is_authenticated
        ):
            user = request.user

    header = context.get("header_user") or {}
    user_uuid = kwargs.pop("user_uuid", None) or header.get("user_uuid")
    if user is None and user_uuid:
        kwargs.setdefault("user_uuid", user_uuid)
        from django.urls import reverse

        return reverse(view_name, kwargs=kwargs)

    if user is None:
        from django.urls import NoReverseMatch, reverse

        try:
            return reverse(view_name, kwargs=kwargs)
        except NoReverseMatch:
            return "#"

    if view_name.startswith("recruiter_"):
        return PortalURLService.recruiter(user, view_name, **kwargs)
    if view_name.startswith("professor_"):
        return PortalURLService.professor(user, view_name, **kwargs)
    if view_name.startswith("college_"):
        return PortalURLService.college(user, view_name, **kwargs)
    return PortalURLService.jobseeker(user, view_name, **kwargs)
