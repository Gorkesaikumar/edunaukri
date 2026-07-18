"""Backward-compatible role permission exports — canonical definitions live in apps.core.permissions.roles."""

from apps.core.permissions.roles import IsCollege, IsJobSeeker, IsProfessor, IsRecruiter

__all__ = ["IsJobSeeker", "IsRecruiter", "IsProfessor", "IsCollege"]
