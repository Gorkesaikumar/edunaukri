from django.shortcuts import render


class MaintenanceModeMiddleware:
    """Intercepts requests and returns a maintenance page if maintenance mode is enabled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from apps.core.services.config import get_setting

        maintenance_enabled = get_setting(
            "platform.maintenance_mode", {"enabled": False}
        ).get("enabled", False)

        if maintenance_enabled:
            path = request.path_info

            # Allow super admin and admin routes to pass through
            if path.startswith("/super-admin/") or path.startswith("/admin/"):
                return self.get_response(request)

            # Allow static and media routes to pass through
            if path.startswith("/static/") or path.startswith("/media/"):
                return self.get_response(request)

            # Allow health check to pass through
            if path.startswith("/health/"):
                return self.get_response(request)

            return render(request, "pages/maintenance.html", status=503)

        return self.get_response(request)
