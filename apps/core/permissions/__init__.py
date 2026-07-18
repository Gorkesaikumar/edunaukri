from apps.core.permissions.base import (
    DomainPermissionBase,
    IsCollegeUser,
    IsFacultyDomainUser,
    IsITDomainUser,
    IsPlatformAdmin,
    IsProfessorUser,
)
from apps.core.permissions.owner import IsOwner
from apps.core.permissions.roles import (
    IsAdmin,
    IsCollege,
    IsITJobSeeker,
    IsITRecruiter,
    IsJobSeeker,
    IsProfessor,
    IsRecruiter,
)

__all__ = [
    "IsPlatformAdmin",
    "IsAdmin",
    "IsITDomainUser",
    "IsProfessorUser",
    "IsProfessor",
    "IsCollegeUser",
    "IsCollege",
    "IsFacultyDomainUser",
    "IsJobSeeker",
    "IsRecruiter",
    "IsITJobSeeker",
    "IsITRecruiter",
    "DomainPermissionBase",
    "IsOwner",
]
