from django.utils.dateparse import parse_datetime

from apps.search.constants.enums import MatchMode, SearchResource
from apps.search.constants.field_registry import get_resource_config
from apps.search.validators.search_validators import SearchValidator


class FilterService:
    """Parse and normalize query parameters into validated search filters."""

    BOOL_TRUE = frozenset({"1", "true", "yes", "on"})
    BOOL_FALSE = frozenset({"0", "false", "no", "off"})

    def parse(self, resource: str, query_params) -> dict:
        config = get_resource_config(resource)
        query_key = config["query_param"]
        raw_query = query_params.get(query_key, "") or query_params.get("search", "")
        params = {
            "query": SearchValidator.validate_query(raw_query),
            "match_mode": self._match_mode(query_params.get("match")),
            "sort": SearchValidator.validate_sort(resource, query_params.get("sort")),
            "page": query_params.get("page"),
            "page_size": query_params.get("page_size"),
            "pagination_mode": query_params.get("pagination_mode", "page"),
        }
        for field, ftype in config["filter_fields"].items():
            raw = query_params.get(field)
            if raw is None or raw == "":
                continue
            params[field] = self._coerce(ftype, raw)
        return params

    def parse_list_param(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [part.strip() for part in value.split(",") if part.strip()]

    def _coerce(self, ftype: str, raw):
        if ftype == "bool":
            return self._parse_bool(raw)
        if ftype == "int":
            try:
                return int(raw)
            except (TypeError, ValueError):
                return None
        if ftype == "decimal":
            return raw
        if ftype == "list":
            return self.parse_list_param(raw)
        if ftype == "date":
            return parse_datetime(raw) or raw
        if ftype == "uuid":
            return raw
        return raw

    @classmethod
    def _parse_bool(cls, value):
        if value is None or value == "":
            return None
        lowered = str(value).lower()
        if lowered in cls.BOOL_TRUE:
            return True
        if lowered in cls.BOOL_FALSE:
            return False
        return None

    @classmethod
    def _match_mode(cls, value: str | None) -> str:
        if value in MatchMode.values:
            return value
        return MatchMode.CONTAINS

    def map_jobs_params(self, params: dict) -> dict:
        skills = params.get("skills")
        if isinstance(skills, str):
            skills = self.parse_list_param(skills)
        return {
            "query": params.get("query", ""),
            "location": params.get("location", ""),
            "employment_type": params.get("employment_type", ""),
            "work_mode": params.get("work_mode", ""),
            "is_remote": params.get("is_remote"),
            "skills": skills or None,
            "experience": params.get("experience"),
            "salary_min": params.get("salary_min"),
            "salary_max": params.get("salary_max"),
            "sort": params.get("sort", "recent"),
        }

    def map_faculty_params(self, params: dict) -> dict:
        return {
            "query": params.get("query", ""),
            "department": params.get("department", ""),
            "qualification": params.get("qualification", ""),
            "designation": params.get("designation", ""),
            "specialization": params.get("specialization", ""),
            "location": params.get("location", ""),
            "employment_type": params.get("employment_type", ""),
            "work_type": params.get("work_type", ""),
            "experience": params.get("experience"),
            "salary_min": params.get("salary_min"),
            "salary_max": params.get("salary_max"),
            "sort": params.get("sort", "recent"),
        }

    def map_applications_params(self, params: dict) -> dict:
        return {
            "query": params.get("query", ""),
            "status": params.get("status", ""),
            "domain": params.get("domain", ""),
            "company_id": params.get("company_id"),
            "college_id": params.get("college_id"),
            "job_posting_id": params.get("job_posting_id"),
            "vacancy_id": params.get("vacancy_id"),
            "sort": params.get("sort", "recent"),
        }

    def map_invoices_params(self, params: dict) -> dict:
        return {
            "domain": params.get("domain"),
            "status": params.get("status"),
            "payment_status": params.get("payment_status"),
            "q": params.get("query", ""),
            "issued_from": params.get("issued_from"),
            "issued_to": params.get("issued_to"),
            "ordering": params.get("sort", "-created_at"),
        }
