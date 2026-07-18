"""Billing and invoice access permissions."""

from rest_framework.permissions import BasePermission

from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.colleges.selectors.college_selector import CollegeMemberSelector
from apps.companies.selectors.company_selector import CompanyMemberSelector
from apps.core.constants.enums import EntityReferenceType
from apps.core.permissions.roles import IsRecruiter
from apps.it_recruitment.selectors.profile_selector import RecruiterProfileSelector


def _recruiter_company_ids(user):
    recruiter = RecruiterProfileSelector().for_user(user)
    if not recruiter:
        return []
    return list(
        CompanyMemberSelector()
        .for_recruiter(recruiter)
        .values_list("company_id", flat=True)
    )


def _college_ids(user):
    if not isinstance(user, CollegeUser):
        return []
    return list(
        CollegeMemberSelector().for_user(user).values_list("college_id", flat=True)
    )


class CanViewBillingInvoice(BasePermission):
    """Recruiters and colleges may view invoices billed to their entities; admins see all."""

    message = "You do not have access to this invoice."

    def has_object_permission(self, request, view, obj):
        if isinstance(request.user, AdminUser):
            return True
        if isinstance(request.user, ITUser) and IsRecruiter().has_permission(
            request, view
        ):
            return (
                obj.bill_to_entity_type == EntityReferenceType.IT_COMPANY
                and obj.bill_to_entity_id in _recruiter_company_ids(request.user)
            )
        if isinstance(request.user, CollegeUser):
            return (
                obj.bill_to_entity_type == EntityReferenceType.FACULTY_COLLEGE
                and obj.bill_to_entity_id in _college_ids(request.user)
            )
        return False


class CanSubmitGuaranteeClaim(BasePermission):
    """Bill-to entity members may submit guarantee claims."""

    message = "You cannot submit guarantee claims for this invoice."

    def has_object_permission(self, request, view, obj):
        return CanViewBillingInvoice().has_object_permission(request, view, obj)
