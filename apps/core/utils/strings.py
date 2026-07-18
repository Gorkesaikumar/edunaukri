import re
import uuid


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def slugify(value: str) -> str:
    value = (value or "").lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[\s_-]+", "-", value).strip("-")


def truncate(value: str, *, max_length: int = 255) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
