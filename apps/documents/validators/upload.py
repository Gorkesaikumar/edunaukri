import re
from pathlib import Path

from django.core.exceptions import ValidationError

from apps.documents.constants.enums import StorageFileType

ALLOWED_EXTENSIONS = {
    StorageFileType.RESUME: {".pdf", ".docx"},
    StorageFileType.CV: {".pdf", ".docx"},
    StorageFileType.CERTIFICATE: {".pdf", ".jpg", ".jpeg", ".png"},
    StorageFileType.PROFILE_PHOTO: {".jpg", ".jpeg", ".png", ".webp"},
    StorageFileType.COMPANY_LOGO: {".jpg", ".jpeg", ".png", ".svg"},
    StorageFileType.COLLEGE_LOGO: {".jpg", ".jpeg", ".png", ".svg", ".webp"},
    StorageFileType.COLLEGE_BANNER: {".jpg", ".jpeg", ".png", ".webp"},
    StorageFileType.INVOICE_PDF: {".pdf"},
    StorageFileType.CLAIM_DOCUMENT: {".pdf", ".jpg", ".jpeg", ".png"},
    StorageFileType.OTHER: {".pdf", ".csv", ".xlsx"},
}

ALLOWED_MIME_TYPES = {
    StorageFileType.RESUME: {
        ".pdf": {"application/pdf", "application/x-pdf"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
    },
    StorageFileType.CV: {
        ".pdf": {"application/pdf", "application/x-pdf"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
    },
    StorageFileType.CERTIFICATE: {
        ".pdf": {"application/pdf", "application/x-pdf"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
    },
    StorageFileType.PROFILE_PHOTO: {
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
        ".webp": {"image/webp"},
    },
    StorageFileType.COMPANY_LOGO: {
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
        ".svg": {"image/svg+xml", "text/xml", "text/plain"},
    },
    StorageFileType.COLLEGE_LOGO: {
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
        ".svg": {"image/svg+xml", "text/xml", "text/plain"},
        ".webp": {"image/webp"},
    },
    StorageFileType.COLLEGE_BANNER: {
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
        ".webp": {"image/webp"},
    },
    StorageFileType.INVOICE_PDF: {
        ".pdf": {"application/pdf", "application/x-pdf"},
    },
    StorageFileType.CLAIM_DOCUMENT: {
        ".pdf": {"application/pdf", "application/x-pdf"},
        ".jpg": {"image/jpeg"},
        ".jpeg": {"image/jpeg"},
        ".png": {"image/png"},
    },
    StorageFileType.OTHER: {
        ".pdf": {"application/pdf", "application/x-pdf"},
        ".csv": {"text/csv", "text/plain"},
        ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip", "application/octet-stream"},
    },
}

MAX_FILE_SIZE_BYTES = {
    StorageFileType.RESUME: 5 * 1024 * 1024,
    StorageFileType.CV: 5 * 1024 * 1024,
    StorageFileType.CERTIFICATE: 5 * 1024 * 1024,
    StorageFileType.PROFILE_PHOTO: 2 * 1024 * 1024,
    StorageFileType.COMPANY_LOGO: 2 * 1024 * 1024,
    StorageFileType.COLLEGE_LOGO: 2 * 1024 * 1024,
    StorageFileType.COLLEGE_BANNER: 5 * 1024 * 1024,
    StorageFileType.INVOICE_PDF: 10 * 1024 * 1024,
    StorageFileType.CLAIM_DOCUMENT: 10 * 1024 * 1024,
    StorageFileType.OTHER: 10 * 1024 * 1024,
}

USER_FRIENDLY_SIZE_MESSAGES = {
    StorageFileType.RESUME: "Resume size cannot exceed 5 MB.",
    StorageFileType.CV: "File size cannot exceed 5 MB.",
    StorageFileType.CERTIFICATE: "Certificate size cannot exceed 5 MB.",
}


def sanitize_original_filename(filename: str) -> str:
    """Strip path segments and unsafe characters from the client filename."""
    clean = Path(filename or "upload").name.strip()
    clean = re.sub(r"[^\w.\- ]", "_", clean)
    clean = re.sub(r"_+", "_", clean).strip("._ ")
    return (clean or "upload")[:500]


class UploadValidator:
    @classmethod
    def validate(cls, *, uploaded_file, file_type: str) -> None:
        if uploaded_file.size <= 0:
            raise ValidationError("Uploaded file is empty.")

        from apps.core.services.config import get_setting

        global_max_mb = get_setting("limits.max_upload_mb", {"mb": 10}).get("mb", 10)

        # We can either override everything with the global limit, or take the min of global limit and the specific file type limit.
        # The prompt says: "Apply this globally to: Resume uploads, Profile images... The upload validator should immediately enforce the new limit."
        # This implies it should act as a hard cap.
        default_max_size = MAX_FILE_SIZE_BYTES.get(file_type, 10 * 1024 * 1024)
        max_size = min(default_max_size, global_max_mb * 1024 * 1024)

        if uploaded_file.size > max_size:
            message = USER_FRIENDLY_SIZE_MESSAGES.get(
                file_type,
                f"File exceeds maximum size of {max_size // (1024 * 1024)} MB.",
            )
            # If the global limit was the restricting factor, update message
            if max_size == global_max_mb * 1024 * 1024:
                message = (
                    f"File exceeds maximum platform size limit of {global_max_mb} MB."
                )
            raise ValidationError(message)

        # Virus Scan Hook
        from apps.documents.services.virus_scanner import VirusScannerService
        VirusScannerService.scan_file(uploaded_file)

        extension = (
            "." + uploaded_file.name.rsplit(".", 1)[-1].lower()
            if "." in uploaded_file.name
            else ""
        )
        allowed = ALLOWED_EXTENSIONS.get(file_type, set())
        if extension not in allowed:
            if file_type == StorageFileType.RESUME:
                raise ValidationError("Only PDF and DOCX resume files are allowed.")
            if file_type == StorageFileType.CERTIFICATE:
                raise ValidationError(
                    "Only PDF, JPG, JPEG, and PNG certificate files are allowed."
                )
            raise ValidationError(
                f"File type '{extension}' is not allowed for {file_type}."
            )

        mime_map = ALLOWED_MIME_TYPES.get(file_type, {})
        if extension in mime_map:
            allowed_mimes = mime_map[extension]
            
            # Use python-magic for deep MIME type inspection
            import magic
            
            original_pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
            try:
                uploaded_file.seek(0)
                chunk = uploaded_file.read(2048)
                detected_mime = magic.from_buffer(chunk, mime=True)
            finally:
                uploaded_file.seek(original_pos)
            
            if detected_mime and detected_mime not in allowed_mimes:
                if file_type == StorageFileType.RESUME:
                    raise ValidationError(
                        "Invalid resume file type. The file signature does not match a valid PDF or DOCX file."
                    )
                raise ValidationError(
                    "File content type does not match the file extension or is invalid."
                )
