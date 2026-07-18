from rest_framework import serializers

from apps.documents.constants.enums import StorageFileType
from apps.documents.models import StoredFile


class StoredFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredFile
        fields = (
            "id",
            "domain",
            "file_type",
            "original_filename",
            "mime_type",
            "file_size_bytes",
            "status",
            "owner_type",
            "owner_id",
            "created_at",
        )
        read_only_fields = fields


from apps.core.validators.common import validate_file_extension

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    file_type = serializers.ChoiceField(choices=StorageFileType.choices)
    owner_type = serializers.CharField(max_length=50)
    owner_id = serializers.UUIDField()

    def validate(self, attrs):
        file = attrs.get('file')
        file_type = attrs.get('file_type')
        if file and file_type:
            if file_type in [StorageFileType.PROFILE_PHOTO, StorageFileType.COMPANY_LOGO, StorageFileType.COLLEGE_LOGO, StorageFileType.COLLEGE_BANNER]:
                validate_file_extension(file, allowed_extensions=['.png', '.jpg', '.jpeg', '.webp'])
            elif file_type in [StorageFileType.RESUME, StorageFileType.CV, StorageFileType.INVOICE_PDF]:
                validate_file_extension(file, allowed_extensions=['.pdf', '.doc', '.docx'])
            else:
                validate_file_extension(file, allowed_extensions=['.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg'])
        return attrs
