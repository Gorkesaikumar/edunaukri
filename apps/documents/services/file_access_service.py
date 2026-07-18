from django.core.exceptions import PermissionDenied

from apps.accounts.models.admin_user import AdminUser
from apps.core.services.base import BaseService
from apps.documents.constants.enums import StorageFileStatus
from apps.documents.models import StoredFile


class FileAccessService(BaseService):
    def assert_can_access(self, *, user, stored_file: StoredFile) -> None:
        if isinstance(user, AdminUser):
            return
        if str(stored_file.owner_id) != str(user.pk):
            raise PermissionDenied("You do not have access to this file.")
        if stored_file.is_deleted or stored_file.status != StorageFileStatus.ACTIVE:
            raise PermissionDenied("File is not available.")

    def assert_can_upload(self, *, user, owner_id) -> None:
        if isinstance(user, AdminUser):
            return
        if str(owner_id) != str(user.pk):
            raise PermissionDenied("Cannot upload files for another user.")
