"""Build Django STORAGES dict from environment variables."""

from pathlib import Path


def build_storages(env, base_dir: Path) -> dict:
    backend = env("STORAGE_BACKEND", default="local").lower()

    if backend == "s3":
        bucket = env("AWS_STORAGE_BUCKET_NAME")
        return {
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    "bucket_name": bucket,
                    "region_name": env("AWS_S3_REGION_NAME", default="ap-south-1"),
                    "custom_domain": env("AWS_S3_CUSTOM_DOMAIN", default=""),
                    "default_acl": env("AWS_DEFAULT_ACL", default="private"),
                    "file_overwrite": False,
                },
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }

    media_root = env("MEDIA_ROOT", default=str(base_dir / "media"))
    return {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
            "OPTIONS": {"location": media_root},
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
