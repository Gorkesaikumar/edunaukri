from pathlib import Path

from django.conf import settings

from apps.core.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Store files on the local filesystem under MEDIA_ROOT."""

    def __init__(self, root: Path | None = None):
        self.root = root or Path(settings.MEDIA_ROOT)

    def _absolute(self, relative_path: str) -> Path:
        return self.root / relative_path.replace("\\", "/")

    def save(self, *, relative_path: str, content: bytes) -> str:
        absolute = self._absolute(relative_path)
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_bytes(content)
        return relative_path.replace("\\", "/")

    def open(self, *, relative_path: str) -> Path:
        return self._absolute(relative_path)

    def delete(self, *, relative_path: str) -> None:
        absolute = self._absolute(relative_path)
        if absolute.exists():
            absolute.unlink()

    def exists(self, *, relative_path: str) -> bool:
        return self._absolute(relative_path).exists()
