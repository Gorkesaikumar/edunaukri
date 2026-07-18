from apps.academic_recruitment.models import ProfessorProfile
from apps.colleges.models import College
from apps.companies.models import Company
from apps.core.selectors.read import ReadSelector
from apps.guarantee_claims.models import GuaranteeClaim
from apps.it_recruitment.models import JobSeekerProfile, RecruiterProfile
from apps.search.constants.enums import SearchResource
from apps.search.query.search_query_builder import SearchQueryBuilder
from apps.search.selectors.search_selector import SearchSelector
from apps.search.services.sorting_service import SortingService


class CompanySearchSelector(SearchSelector):
    resource = SearchResource.COMPANIES
    model = Company

    def get_base_queryset(self, **params):
        qs = self.filter_by()
        if params.get("public_only", True):
            qs = qs.filter(Q(is_active=True, is_deleted=False))
        return qs

    def search(self, **params):
        qs = self.get_base_queryset(**params)
        builder = self.using_builder(qs, **params)
        builder.apply_filter("verification_status", params.get("verification_status"))
        builder.apply_boolean("is_active", params.get("is_active"))
        builder.apply_filter("industry", params.get("industry"), lookup="icontains")
        builder.apply_filter("city", params.get("city"), lookup="icontains")
        builder.apply_date_range(
            "created_at", params.get("created_after"), params.get("created_before")
        )
        order = SortingService().resolve(self.resource, params.get("sort"))
        if isinstance(order, tuple):
            builder.apply_ordering(*order)
        else:
            builder.apply_ordering(order)
        return builder.build()


class CollegeSearchSelector(SearchSelector):
    resource = SearchResource.COLLEGES
    model = College

    def get_base_queryset(self, **params):
        qs = self.filter_by()
        if params.get("public_only", True):
            qs = qs.filter(Q(is_active=True, is_deleted=False))
        return qs

    def search(self, **params):
        qs = self.get_base_queryset(**params)
        builder = self.using_builder(qs, **params)
        builder.apply_filter("verification_status", params.get("verification_status"))
        builder.apply_boolean("is_active", params.get("is_active"))
        builder.apply_filter("city", params.get("city"), lookup="icontains")
        builder.apply_filter("state", params.get("state"), lookup="icontains")
        builder.apply_date_range(
            "created_at", params.get("created_after"), params.get("created_before")
        )
        order = SortingService().resolve(self.resource, params.get("sort"))
        if isinstance(order, tuple):
            builder.apply_ordering(*order)
        else:
            builder.apply_ordering(order)
        return builder.build()


class JobSeekerSearchSelector(SearchSelector):
    resource = SearchResource.JOB_SEEKERS
    model = JobSeekerProfile

    def get_base_queryset(self, **params):
        return self.model.profiles.with_active_status().select_related("user")

    def search(self, *, viewer=None, **params):
        qs = self.get_base_queryset(**params)
        if viewer is not None:
            from apps.it_recruitment.services.jobseeker_privacy_service import (
                JobSeekerPrivacyService,
            )

            qs = JobSeekerPrivacyService().filter_searchable_queryset(qs, viewer)
        builder = self.using_builder(qs, **params)
        builder.apply_filter("profile_status", params.get("profile_status"))
        builder.apply_filter(
            "current_location", params.get("location"), lookup="icontains"
        )
        builder.apply_int_range(
            "experience_years",
            params.get("experience_min"),
            params.get("experience_max"),
        )
        builder.apply_date_range(
            "created_at", params.get("created_after"), params.get("created_before")
        )
        order = SortingService().resolve(self.resource, params.get("sort"))
        if isinstance(order, tuple):
            builder.apply_ordering(*order)
        else:
            builder.apply_ordering(order)
        return builder.build()


class RecruiterSearchSelector(SearchSelector):
    resource = SearchResource.RECRUITERS
    model = RecruiterProfile

    def get_base_queryset(self, **params):
        return self.model.profiles.with_active_status().select_related("user")

    def search(self, **params):
        qs = self.get_base_queryset(**params)
        builder = self.using_builder(qs, **params)
        builder.apply_filter("profile_status", params.get("profile_status"))
        builder.apply_date_range(
            "created_at", params.get("created_after"), params.get("created_before")
        )
        order = SortingService().resolve(self.resource, params.get("sort"))
        if isinstance(order, tuple):
            builder.apply_ordering(*order)
        else:
            builder.apply_ordering(order)
        return builder.build()


class ProfessorSearchSelector(SearchSelector):
    resource = SearchResource.PROFESSORS
    model = ProfessorProfile

    def get_base_queryset(self, **params):
        return self.model.profiles.with_active_status().select_related("user")

    def search(self, **params):
        qs = self.get_base_queryset(**params)
        builder = self.using_builder(qs, **params)
        builder.apply_filter("profile_status", params.get("profile_status"))
        builder.apply_filter(
            "specialization", params.get("specialization"), lookup="icontains"
        )
        builder.apply_int_range(
            "experience_years",
            params.get("experience_min"),
            params.get("experience_max"),
        )
        builder.apply_date_range(
            "created_at", params.get("created_after"), params.get("created_before")
        )
        order = SortingService().resolve(self.resource, params.get("sort"))
        if isinstance(order, tuple):
            builder.apply_ordering(*order)
        else:
            builder.apply_ordering(order)
        return builder.build()


class GuaranteeSearchSelector(SearchSelector):
    resource = SearchResource.GUARANTEES
    model = GuaranteeClaim

    def get_base_queryset(self, **params):
        return self.filter_by()

    def search(self, **params):
        qs = self.get_base_queryset(**params)
        builder = self.using_builder(qs, **params)
        builder.apply_filter("domain", params.get("domain"))
        builder.apply_filter("status", params.get("status"))
        builder.apply_filter("claim_type", params.get("claim_type"))
        builder.apply_date_range(
            "submitted_at", params.get("submitted_from"), params.get("submitted_to")
        )
        order = SortingService().resolve(self.resource, params.get("sort"))
        builder.apply_ordering(order)
        return builder.build()


class AdminGlobalSearchSelector(ReadSelector):
    """Cross-domain admin search returning grouped result summaries."""

    def search(
        self, *, query: str = "", domain: str = "", resource: str = "", limit: int = 5
    ) -> dict:
        from apps.admin_panel.selectors.user_selector import UserSelector

        results = {"query": query, "groups": []}
        if not query:
            return results
        users = UserSelector().list_users(domain=domain or None, search=query)[:limit]
        if users:
            results["groups"].append(
                {"resource": "users", "count": len(users), "results": users}
            )
        if not resource or resource == "companies":
            companies = CompanySearchSelector().search(query=query, public_only=False)[
                :limit
            ]
            if companies.exists():
                results["groups"].append(
                    {
                        "resource": "companies",
                        "count": companies.count(),
                        "ids": [str(c.pk) for c in companies],
                    }
                )
        if not resource or resource == "colleges":
            colleges = CollegeSearchSelector().search(query=query, public_only=False)[
                :limit
            ]
            if colleges.exists():
                results["groups"].append(
                    {
                        "resource": "colleges",
                        "count": colleges.count(),
                        "ids": [str(c.pk) for c in colleges],
                    }
                )
        return results
