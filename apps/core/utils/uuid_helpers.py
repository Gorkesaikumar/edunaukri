import uuid


def ensure_uuid(value) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def uuid_to_str(value) -> str:
    if value is None:
        return ""
    return str(value)
