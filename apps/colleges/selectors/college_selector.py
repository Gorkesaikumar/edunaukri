from apps.colleges.constants.enums import CollegeMemberRole
from apps.colleges.models import (
    College,
    CollegeDepartment,
    CollegeMember,
    Department,
    InstitutionCampus,
    InstitutionDocument,
)
from apps.core.selectors.read import ReadSelector


class CollegeSelector(ReadSelector):
    model = College
    search_fields = ("name", "legal_name", "city", "district", "state")

    def get_active(self, college_id):
        return self.model.profiles.with_active_status().filter(pk=college_id).first()

    def get_or_none(self, college_id):
        return self.filter_by(pk=college_id).first()

    def for_college_user(self, college_user):
        college_ids = (
            CollegeMemberSelector()
            .for_user(college_user)
            .values_list("college_id", flat=True)
        )
        return self.filter_by(pk__in=college_ids).order_by("name")

    def verified(self):
        return self.filter_by(is_active=True).order_by("name")

    def admin_list(self, *, is_active=None, search: str | None = None):
        queryset = self.filter_by()
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if search:
            queryset = queryset.filter(name__icontains=search)
        return queryset.order_by("name")


# Institution-facing alias used by the new module (same read semantics).
InstitutionSelector = CollegeSelector


class CollegeMemberSelector(ReadSelector):
    model = CollegeMember

    def for_user(self, college_user):
        return self.filter_by(college_user=college_user, is_active=True)

    def for_college(self, college_id):
        return (
            self.filter_by(college_id=college_id, is_active=True)
            .select_related("college_user")
            .order_by("-is_primary", "role")
        )

    def primary_for_user(self, college_user):
        return self.for_user(college_user).filter(is_primary=True).first()

    def has_active_membership(self, college_user) -> bool:
        return self.for_user(college_user).exists()

    def is_member(self, college_user, college_id) -> bool:
        return self.for_user(college_user).filter(college_id=college_id).exists()

    def is_admin(self, college_user, college_id) -> bool:
        return (
            self.for_user(college_user)
            .filter(
                college_id=college_id,
                role__in=[CollegeMemberRole.OWNER, CollegeMemberRole.ADMIN],
            )
            .exists()
        )

    def is_owner(self, college_user, college_id) -> bool:
        return (
            self.for_user(college_user)
            .filter(college_id=college_id, role=CollegeMemberRole.OWNER)
            .exists()
        )

    def membership(self, college_user, college_id):
        return self.for_user(college_user).filter(college_id=college_id).first()


class DepartmentSelector(ReadSelector):
    model = Department
    search_fields = ("name", "category")

    def active(self):
        return self.filter_by(is_active=True).order_by("name")


class CollegeDepartmentSelector(ReadSelector):
    model = CollegeDepartment

    def for_college(self, college_id):
        return self.filter_by(college_id=college_id).order_by("department__name")


class InstitutionCampusSelector(ReadSelector):
    model = InstitutionCampus

    def for_college(self, college_id):
        return self.filter_by(college_id=college_id).order_by("-is_main_campus", "city")


class InstitutionDocumentSelector(ReadSelector):
    model = InstitutionDocument

    def for_college(self, college_id, *, document_type: str | None = None):
        queryset = self.filter_by(college_id=college_id)
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        return queryset.order_by("-created_at")


class InstitutionDashboardSelector(ReadSelector):
    model = College

    def summary_for_user(self, college_user) -> dict:
        colleges = CollegeSelector().for_college_user(college_user)
        return {
            "total_institutions": colleges.count(),
            "active_institutions": colleges.filter(is_active=True).count(),
        }

    def platform_summary(self) -> dict:
        colleges = CollegeSelector().filter_by()
        return {
            "total_institutions": colleges.count(),
            "active_institutions": colleges.filter(is_active=True).count(),
        }
