from abc import ABC, abstractmethod
from pathlib import Path


class StorageBackend(ABC):
    """Abstract storage backend for media files."""

    @abstractmethod
    def save(self, *, relative_path: str, content: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def open(self, *, relative_path: str) -> Path:
        raise NotImplementedError

    @abstractmethod
    def delete(self, *, relative_path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, *, relative_path: str) -> bool:
        raise NotImplementedError
