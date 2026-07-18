from django.contrib import admin

from apps.documents.models import StoredFile


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "domain",
        "file_type",
        "status",
        "file_size_bytes",
        "created_at",
        "is_deleted",
    )
    list_filter = ("domain", "file_type", "status", "is_deleted")
    search_fields = ("original_filename", "storage_path", "checksum_sha256")
    readonly_fields = (
        "id",
        "stored_filename",
        "storage_path",
        "checksum_sha256",
        "created_at",
        "updated_at",
        "deleted_at",
        "parsed_at",
    )
