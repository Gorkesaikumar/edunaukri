from django.conf import settings

from apps.core.services.base import BaseService
from apps.core.storage.local import LocalStorageBackend
from apps.core.storage.s3 import S3StorageBackend


def get_storage_backend():
    backend = getattr(settings, "STORAGE_BACKEND", "local")
    if backend == "s3":
        return S3StorageBackend(
            bucket=getattr(settings, "AWS_STORAGE_BUCKET_NAME", ""),
            region=getattr(settings, "AWS_S3_REGION_NAME", None),
        )
    return LocalStorageBackend()


class StorageService(BaseService):
    """Media storage abstraction used by domain upload services."""

    def __init__(self, backend=None):
        self.backend = backend or get_storage_backend()

    def save_bytes(self, *, relative_path: str, content: bytes) -> str:
        return self.backend.save(relative_path=relative_path, content=content)

    def open_path(self, *, relative_path: str):
        return self.backend.open(relative_path=relative_path)

    def delete_file(self, *, relative_path: str) -> None:
        self.backend.delete(relative_path=relative_path)

    def file_exists(self, *, relative_path: str) -> bool:
        return self.backend.exists(relative_path=relative_path)
