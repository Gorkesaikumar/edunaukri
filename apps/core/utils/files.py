import hashlib
import uuid
from pathlib import Path


def sha256_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_uploaded_file(uploaded_file, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    with destination.open("wb") as handle:
        for chunk in uploaded_file.chunks():
            handle.write(chunk)
            digest.update(chunk)
    return digest.hexdigest()


def safe_filename(filename: str) -> str:
    return Path(filename).name.replace(" ", "_")
