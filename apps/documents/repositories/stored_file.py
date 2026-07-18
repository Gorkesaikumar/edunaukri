from apps.core.repositories.base import BaseRepository
from apps.documents.constants.enums import StorageFileStatus
from apps.documents.models import StoredFile


class StoredFileRepository(BaseRepository):
    model = StoredFile

    def create(self, **kwargs) -> StoredFile:
        return StoredFile.objects.create(**kwargs)

    def get_by_id(self, file_id) -> StoredFile | None:
        try:
            return StoredFile.objects.get(pk=file_id)
        except StoredFile.DoesNotExist:
            return None

    def soft_delete(self, stored_file: StoredFile) -> StoredFile:
        stored_file.delete()
        stored_file.status = StorageFileStatus.DELETED
        stored_file.save(update_fields=["status"])
        return stored_file
