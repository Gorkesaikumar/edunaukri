from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_panel"
    verbose_name = "Enterprise Admin Panel"

    def ready(self):
        from apps.admin_panel import signals  # noqa: F401
