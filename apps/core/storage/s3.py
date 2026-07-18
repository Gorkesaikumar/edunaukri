from apps.core.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    """S3-compatible storage hook — configure STORAGE_BACKEND=s3 in production."""

    def __init__(self, *, bucket: str, region: str | None = None):
        self.bucket = bucket
        self.region = region

    def save(self, *, relative_path: str, content: bytes) -> str:
        raise NotImplementedError(
            "Configure django-storages and boto3 to enable S3 uploads."
        )

    def open(self, *, relative_path: str):
        raise NotImplementedError(
            "Configure django-storages and boto3 to enable S3 downloads."
        )

    def delete(self, *, relative_path: str) -> None:
        raise NotImplementedError(
            "Configure django-storages and boto3 to enable S3 deletes."
        )

    def exists(self, *, relative_path: str) -> bool:
        raise NotImplementedError(
            "Configure django-storages and boto3 to enable S3 existence checks."
        )
