from apps.companies.models import Company, CompanyLocation, CompanyMember
from apps.core.selectors.read import ReadSelector


class CompanySelector(ReadSelector):
    model = Company
    search_fields = ("name", "legal_name", "industry", "headquarters_location", "city")

    def for_recruiter(self, recruiter):
        company_ids = (
            CompanyMemberSelector()
            .for_recruiter(recruiter)
            .values_list("company_id", flat=True)
        )
        return self.filter_by(pk__in=company_ids).order_by("name")

    def verified(self):
        return self.filter_by(is_active=True).order_by("name")

    def get_or_none(self, company_id):
        return self.filter_by(pk=company_id).first()

    def admin_list(self, *, is_active=None, search: str | None = None):
        queryset = self.filter_by()
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name")


class CompanyMemberSelector(ReadSelector):
    model = CompanyMember

    def for_recruiter(self, recruiter):
        return self.filter_by(recruiter=recruiter, is_active=True)

    def for_company(self, company_id):
        return self.filter_by(company_id=company_id, is_active=True).order_by(
            "-is_primary", "role"
        )

    def is_member(self, recruiter, company_id) -> bool:
        return self.for_recruiter(recruiter).filter(company_id=company_id).exists()

    def is_owner(self, recruiter, company_id) -> bool:
        return (
            self.for_recruiter(recruiter)
            .filter(company_id=company_id, role="owner")
            .exists()
        )

    def membership(self, recruiter, company_id):
        return self.for_recruiter(recruiter).filter(company_id=company_id).first()


class CompanyLocationSelector(ReadSelector):
    model = CompanyLocation

    def for_company(self, company_id):
        return self.filter_by(company_id=company_id).order_by(
            "-is_headquarters", "city"
        )


class CompanyDashboardSelector(ReadSelector):
    model = Company

    def summary_for_recruiter(self, recruiter) -> dict:
        companies = CompanySelector().for_recruiter(recruiter)
        return {
            "total_companies": companies.count(),
            "active_companies": companies.filter(is_active=True).count(),
        }

    def platform_summary(self) -> dict:
        companies = CompanySelector().filter_by()
        return {
            "total_companies": companies.count(),
            "active_companies": companies.filter(is_active=True).count(),
        }
