import logging
from typing import Any
from django.core.cache import cache

logger = logging.getLogger(__name__)


def get_setting(key: str, default: Any = None) -> Any:
    """
    Fetch a global platform setting, prioritizing the cache.
    If it's not cached, look up in the database.
    If it's not in the database, return the default value.
    """
    cache_key = f"platform_setting:{key}"
    cached_value = cache.get(cache_key)

    if cached_value is not None:
        return cached_value

    try:
        from apps.admin_panel.models.platform_setting import PlatformSetting

        setting = PlatformSetting.objects.filter(key=key, is_active=True).first()
        if setting:
            value = setting.value
            # Cache for 24 hours. AdminConfigService will invalidate on update.
            cache.set(cache_key, value, timeout=86400)
            return value
    except Exception as exc:
        logger.error(f"Failed to fetch platform setting '{key}' from database: {exc}")

    # Fallback if DB fetch fails or setting doesn't exist
    return default
