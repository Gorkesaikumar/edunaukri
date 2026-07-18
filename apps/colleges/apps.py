from django.apps import AppConfig


class CollegesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.colleges"
    verbose_name = "Colleges"

    def ready(self):
        from apps.colleges import signals  # noqa: F401
