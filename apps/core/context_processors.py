def platform_config(request):
    """Inject global platform settings into all templates."""
    from apps.core.services.config import get_setting

    return {
        "PLATFORM_NAME": get_setting("platform.name", {"name": "EduNaukri"}).get(
            "name", "EduNaukri"
        ),
    }
