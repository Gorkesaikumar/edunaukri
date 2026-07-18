from apps.core.selectors.read import ReadSelector
from apps.documents.models import StoredFile


class StoredFileSelector(ReadSelector):
    model = StoredFile

    def get_active(self, file_id):
        return self.filter_by(pk=file_id).first()
