from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

from apps.authentication.services.web_jwt_service import WebJWTService
from apps.core.constants.enums import DomainType, EntityReferenceType
from apps.invoices.selectors.invoice_selector import InvoiceSelector


class RecruiterInvoicesView(TemplateView):
    """Unified view for Recruiters (IT and College) to see their Invoices."""

    template_name = "invoices/recruiter_invoices_list.html"

    def dispatch(self, request, *args, **kwargs):
        self.user = WebJWTService.get_valid_it_user(request)
        self.domain = DomainType.IT
        self.sidebar_active_key = "invoices"
        self.base_template = "it/recruiter/base_dashboard.html"
        self.entity_type = EntityReferenceType.IT_COMPANY

        if not self.user:
            self.user = WebJWTService.get_valid_college_user(request)
            self.domain = DomainType.FACULTY
            self.base_template = "academic/college/base_dashboard.html"
            self.entity_type = EntityReferenceType.FACULTY_COLLEGE

        if not self.user:
            messages.error(
                request, "You must be logged in as a recruiter to view invoices."
            )
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def _build_it_portal_context(self, profile):
        """Build the full recruiter portal header + sidebar context for IT users."""
        from apps.authentication.services.identity_service import IdentityService
        from apps.authentication.services.portal_url_service import PortalURLService
        from apps.it_recruitment.services.jobseeker_portal_helpers import (
            initials_from_name,
            media_url,
        )
        from apps.it_recruitment.services.recruiter_portal_helpers import (
            build_recruiter_sidebar_nav,
            primary_company_for_recruiter,
        )
        from apps.notifications.models import Notification

        display_name = (
            profile.full_name if profile else self.request.user.email.split("@")[0]
        )
        avatar_url = (
            media_url(profile.profile_image)
            if profile and profile.profile_image
            else None
        )
        unread = Notification.objects.filter(
            recipient_domain="it", recipient_id=self.user.pk, is_read=False
        ).count()

        return {
            "header_user": {
                "display_name": display_name,
                "role_label": "Recruiter",
                "initials": initials_from_name(display_name, self.user.email[:2]),
                "avatar_url": avatar_url,
                "profile_url": PortalURLService.recruiter(self.user, "recruiter_profile"),
                "user_uuid": IdentityService.public_uuid(self.user),
            },
            "unread_notification_count": unread,
            "notifications_url": PortalURLService.recruiter(self.user, "recruiter_notifications"),
            "messages_url": PortalURLService.recruiter(self.user, "recruiter_messages"),
            "logout_url": reverse("logout"),
            "sidebar": build_recruiter_sidebar_nav(self.sidebar_active_key, self.user),
            "company_branding": primary_company_for_recruiter(profile),
            "portal_user_uuid": IdentityService.public_uuid(self.user),
        }
    def _build_faculty_portal_context(self):
        """Build the full recruiter portal header + sidebar context for College users."""
        from apps.authentication.services.identity_service import IdentityService
        from apps.authentication.services.portal_url_service import PortalURLService
        from apps.it_recruitment.services.jobseeker_portal_helpers import initials_from_name
        from apps.academic_recruitment.services.college_portal_helpers import (
            build_college_sidebar,
            primary_institution_for_user,
        )
        from apps.core.portal_header_config import INSTITUTION_RECRUITER_HEADER
        from apps.notifications.models import Notification

        institution = primary_institution_for_user(self.user)
        display_name = (
            institution["name"]
            if institution
            else self.user.email.split("@")[0]
        )
        avatar_url = institution["logo_url"] if institution else None
        unread = Notification.objects.filter(
            recipient_domain="college", recipient_id=self.user.pk, is_read=False
        ).count()

        portal_url = lambda view_name: PortalURLService.college(self.user, view_name)

        return {
            "header_user": {
                "display_name": display_name,
                "role_label": "Institution Recruiter",
                "initials": initials_from_name(display_name, self.user.email[:2]),
                "avatar_url": avatar_url,
                "profile_url": portal_url("college_profile"),
                "user_uuid": IdentityService.public_uuid(self.user),
            },
            "unread_notification_count": unread,
            "notifications_url": portal_url("college_notifications"),
            "messages_url": portal_url("college_messages"),
            "logout_url": reverse("logout"),
            "search_url": portal_url("college_vacancies"),
            "portal_header": INSTITUTION_RECRUITER_HEADER,
            "sidebar": build_college_sidebar(self.sidebar_active_key, self.user),
            "sidebar_profile": {
                "display_name": display_name,
                "headline": institution["verification_label"] if institution else "Institution Recruiter",
            },
            "institution_branding": institution,
            "portal_user_uuid": IdentityService.public_uuid(self.user),
        }


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.domain == DomainType.IT:
            from apps.companies.selectors.company_selector import CompanyMemberSelector

            profile = None
            company_ids = []
            try:
                profile = self.user.recruiter_profile
                company_ids = (
                    CompanyMemberSelector()
                    .for_recruiter(profile)
                    .values_list("company_id", flat=True)
                )
            except Exception:
                pass

            invoices = InvoiceSelector().for_company_ids(company_ids, domain=self.domain)
            context.update(self._build_it_portal_context(profile))
        else:
            from apps.colleges.selectors.college_selector import CollegeMemberSelector

            college_ids = (
                CollegeMemberSelector()
                .for_user(self.user)
                .values_list("college_id", flat=True)
            )
            invoices = InvoiceSelector().for_college_ids(college_ids, domain=self.domain)
            context.update(self._build_faculty_portal_context())

        context["invoices"] = invoices
        context["domain"] = self.domain
        context["base_template"] = self.base_template
        context["sidebar_active_key"] = self.sidebar_active_key
        return context


from django.http import HttpResponse

class RecruiterInvoiceBaseView(TemplateView):
    def dispatch(self, request, *args, **kwargs):
        self.user = WebJWTService.get_valid_it_user(request)
        self.domain = DomainType.IT

        if not self.user:
            self.user = WebJWTService.get_valid_college_user(request)
            self.domain = DomainType.FACULTY

        if not self.user:
            messages.error(
                request, "You must be logged in as a recruiter to view invoices."
            )
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_invoice(self, invoice_id):
        if self.domain == DomainType.IT:
            from apps.companies.selectors.company_selector import CompanyMemberSelector
            try:
                recruiter = self.user.recruiter_profile
                entity_ids = (
                    CompanyMemberSelector()
                    .for_recruiter(recruiter)
                    .values_list("company_id", flat=True)
                )
            except Exception:
                entity_ids = []
        else:
            from apps.colleges.selectors.college_selector import CollegeMemberSelector
            entity_ids = (
                CollegeMemberSelector()
                .for_user(self.user)
                .values_list("college_id", flat=True)
            )

        from django.shortcuts import get_object_or_404
        from apps.invoices.models import Invoice

        return get_object_or_404(
            Invoice, pk=invoice_id, is_deleted=False, bill_to_entity_id__in=entity_ids
        )


class RecruiterInvoiceView(RecruiterInvoiceBaseView):
    def get(self, request, *args, **kwargs):
        invoice = self.get_invoice(kwargs.get("invoice_id"))
        from apps.invoices.services.invoice_rendering_service import InvoiceRenderingService
        html = InvoiceRenderingService(invoice).render_html()
        return HttpResponse(html)


class RecruiterInvoiceDownloadView(RecruiterInvoiceBaseView):
    def get(self, request, *args, **kwargs):
        invoice = self.get_invoice(kwargs.get("invoice_id"))
        from apps.invoices.services.invoice_rendering_service import InvoiceRenderingService
        pdf = InvoiceRenderingService(invoice).render_pdf()
        
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response
