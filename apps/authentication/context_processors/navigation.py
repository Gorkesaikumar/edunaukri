"""Template context processors for authentication-aware UI."""

from apps.authentication.services.navigation_service import NavigationService


def _resolve_active_nav(path: str) -> str:
    """Return the primary nav key for the current request path."""
    if path.startswith("/institutions"):
        return "institutions"
    if path.startswith("/jobs"):
        return "jobs"
    if path.startswith("/about"):
        return "about"
    if path == "/":
        return "home"
    if path.startswith("/sign-in"):
        return "signin"
    if path.startswith("/get-started"):
        return "getstarted"
    return ""


def navigation(request):
    """Expose `nav` dict to all templates for header/sidebar rendering."""
    nav = NavigationService().build(request).to_template_dict()
    nav["active"] = _resolve_active_nav(request.path)
    return {"nav": nav}
