from django.core.exceptions import ValidationError

from apps.core.constants.app_constants import MAX_IMAGE_SIZE_MB, MAX_UPLOAD_SIZE_MB


def validate_file_upload(
    uploaded_file,
    *,
    allowed_extensions: set[str],
    max_size_mb: int | None = None,
) -> None:
    if uploaded_file.size <= 0:
        raise ValidationError("Uploaded file is empty.")

    from apps.core.services.config import get_setting

    global_max = get_setting("limits.max_upload_mb", {"mb": MAX_UPLOAD_SIZE_MB}).get(
        "mb", MAX_UPLOAD_SIZE_MB
    )
    effective_max_mb = min(max_size_mb or global_max, global_max)

    limit = effective_max_mb * 1024 * 1024
    if uploaded_file.size > limit:
        raise ValidationError(f"File exceeds maximum size of {effective_max_mb} MB.")

    extension = (
        "." + uploaded_file.name.rsplit(".", 1)[-1].lower()
        if "." in uploaded_file.name
        else ""
    )
    if extension not in allowed_extensions:
        raise ValidationError(f"File type '{extension}' is not allowed.")


def validate_image_upload(
    uploaded_file, *, allowed_extensions: set[str] | None = None
) -> None:
    extensions = allowed_extensions or {".jpg", ".jpeg", ".png", ".webp", ".svg"}
    validate_file_upload(
        uploaded_file, allowed_extensions=extensions, max_size_mb=MAX_IMAGE_SIZE_MB
    )
