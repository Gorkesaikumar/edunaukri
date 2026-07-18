from apps.search.constants.field_registry import get_resource_config


class SortingService:
    """Resolve sort parameters to Django order_by expressions."""

    _JOB_SORT = {
        "recent": "-published_at",
        "oldest": "published_at",
        "salary_high": "-salary_max",
        "salary_low": "salary_min",
        "title": "title",
        "name": "title",
        "-created_at": "-created_at",
        "created_at": "created_at",
    }

    _FACULTY_SORT = _JOB_SORT

    _APPLICATION_SORT = {
        "recent": "-applied_at",
        "oldest": "applied_at",
        "status": "status",
    }

    _PROFILE_NAME_SORT = {
        "name": ("last_name", "first_name"),
        "-created_at": "-created_at",
        "created_at": "created_at",
        "experience_years": "experience_years",
        "-experience_years": "-experience_years",
    }

    def resolve(self, resource: str, sort: str | None = None) -> str | tuple[str, ...]:
        config = get_resource_config(resource)
        sort = sort or config["default_sort"]
        if resource in ("jobs",):
            return self._JOB_SORT.get(sort, "-published_at")
        if resource in ("faculty", "vacancies"):
            return self._FACULTY_SORT.get(sort, "-published_at")
        if resource == "applications":
            return self._APPLICATION_SORT.get(sort, "-applied_at")
        if resource in ("job_seekers", "recruiters", "professors"):
            resolved = self._PROFILE_NAME_SORT.get(sort)
            if resolved:
                return resolved
        if sort in config["sort_fields"]:
            return sort
        return config["default_sort"]
