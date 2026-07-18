"""Storage helpers — use apps.core.services.storage.StorageService for uploads."""

from apps.core.services.storage import StorageService, get_storage_backend

__all__ = ["StorageService", "get_storage_backend"]
