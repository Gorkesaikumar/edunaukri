"""Enterprise Super Admin web portal views delegating to domain services."""

from __future__ import annotations

import json
import logging
from urllib.parse import quote

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.models.admin_user import AdminUser
from apps.admin_panel.services.admin_analytics_service import AdminAnalyticsService
from apps.admin_panel.services.admin_application_service import AdminApplicationService
from apps.admin_panel.services.admin_audit_service import AdminAuditService
from apps.admin_panel.services.admin_billing_service import (
    AdminGuaranteeService,
    AdminInvoiceService,
)
from apps.admin_panel.services.admin_college_service import AdminCollegeService
from apps.admin_panel.services.admin_company_service import AdminCompanyService
from apps.admin_panel.services.admin_config_service import AdminConfigService
from apps.admin_panel.services.admin_dashboard_service import AdminDashboardService
from apps.admin_panel.services.admin_faculty_service import AdminFacultyService
from apps.admin_panel.services.admin_job_service import AdminJobService
from apps.admin_panel.services.admin_report_service import AdminReportService
from apps.admin_panel.services.admin_user_service import AdminUserService
from apps.authentication.services.portal_url_service import PortalURLService
from apps.authentication.services.web_jwt_service import WebJWTService
from apps.colleges.models import College
from apps.companies.models import Company
from apps.faculty.models import FacultyVacancy
from apps.guarantee_claims.models import GuaranteeClaim
from apps.invoices.models import Invoice
from apps.jobs.models import JobPosting
from apps.applications.selectors.application_selector import (
    JobApplicationSelector,
    FacultyApplicationSelector,
)
from apps.admin_panel.api.v1.serializers import (
    AdminJobApplicationSerializer,
    AdminFacultyApplicationSerializer,
)

logger = logging.getLogger(__name__)


class SuperAdminPortalMixin(LoginRequiredMixin):
    """Shared authentication and layout context for Super Admin portal pages."""

    login_url = "/super-admin/login/"
    sidebar_active_key = "dashboard"
    page_title = "Control Center"
    page_description = "Platform overview and operations"

    def dispatch(self, request, *args, **kwargs):
        user = WebJWTService.resolve_web_user(request)
        if user is None or not isinstance(user, AdminUser):
            return redirect(
                f"{reverse('super_admin_login')}?next={quote(request.get_full_path(), safe='')}"
            )
        user_uuid = str(kwargs.get("user_uuid", ""))
        if user_uuid and user_uuid != str(user.pk):
            target = PortalURLService.super_admin(
                user,
                request.resolver_match.url_name or "super_admin_dashboard",
                **{k: v for k, v in kwargs.items() if k != "user_uuid"},
            )
            return redirect(target)
        request.user = user
        return super().dispatch(request, *args, **kwargs)

    def portal_url(self, view_name: str, **kwargs) -> str:
        return PortalURLService.super_admin(self.request.user, view_name, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        display_name = (
            getattr(user, "full_name", None)
            or getattr(user, "username", None)
            or user.email.split("@")[0]
        )
        context.update(
            {
                "sidebar_active": self.sidebar_active_key,
                "page_title": self.page_title,
                "page_description": self.page_description,
                "header_user": {
                    "display_name": display_name,
                    "role_label": "Super Admin",
                    "initials": display_name[:2].upper(),
                    "avatar_url": None,
                    "user_uuid": str(user.pk),
                    "email": user.email,
                },
                "nav_urls": {
                    "dashboard": self.portal_url("super_admin_dashboard"),
                    "users": self.portal_url("super_admin_users"),
                    "jobs": self.portal_url("super_admin_jobs"),
                    "applications": self.portal_url("super_admin_applications"),
                    "billing": self.portal_url("super_admin_billing"),
                    "claims": self.portal_url("super_admin_claims"),
                    "organizations": self.portal_url("super_admin_organizations"),
                    "analytics": self.portal_url("super_admin_analytics"),
                    "reports": self.portal_url("super_admin_reports"),
                    "settings": self.portal_url("super_admin_settings"),

                    "notifications": self.portal_url("super_admin_notifications"),
                    "support": self.portal_url("super_admin_support"),
                    "invoice_config": self.portal_url("super_admin_invoice_configuration"),
                    "logout": reverse("web_logout"),
                },
            }
        )
        return context


class SuperAdminDashboardView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/dashboard/index.html"
    sidebar_active_key = "dashboard"
    page_title = "Executive Overview"
    page_description = "Real-time system health, revenue KPIs, and moderation queues"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        domain = self.request.GET.get("domain", "all")
        date_range = self.request.GET.get("date_range", "30d")
        
        filters = {
            "domain": domain,
            "date_range": date_range
        }
        
        service = AdminDashboardService()
        context["summary"] = service.summary()
        context["kpis"] = service.kpis(**filters)
        
        analytics_service = AdminAnalyticsService()
        context["bi"] = analytics_service.bi_dashboard_overview(**filters)
        
        context["current_domain"] = domain
        context["current_date_range"] = date_range
        return context


class SuperAdminUserListView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/users/list.html"
    sidebar_active_key = "users"
    page_title = "User Management"
    page_description = (
        "Manage IT seekers, recruiters, faculty members, and institution users"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = self.request.GET.get("domain", "it")
        search = self.request.GET.get("q", "")
        status = self.request.GET.get("status", "")
        org_id = self.request.GET.get("org_id", "")
        service = AdminUserService()
        users = service.list_users(domain=domain, search=search, account_status=status, org_id=org_id)
        context["users"] = users[:100]
        context["current_domain"] = domain
        context["current_search"] = search
        context["current_status"] = status
        context["current_org_id"] = org_id
        return context


class SuperAdminUserDetailView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/users/detail.html"
    sidebar_active_key = "users"
    page_title = "User Details & Security"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = self.request.GET.get("domain", "it")
        user_id = kwargs.get("user_id")
        service = AdminUserService()
        context["user_detail"] = service.get_user(domain=domain, user_id=user_id)
        context["login_history"] = service.login_history(
            domain=domain, user_id=user_id, limit=20
        )
        context["user_activity"] = service.user_activity(
            domain=domain, user_id=user_id, limit=20
        )
        context["current_domain"] = domain
        return context


class SuperAdminUserActionAPIView(SuperAdminPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            action = data.get("action")
            domain = data.get("domain", "it")
            user_id = kwargs.get("user_id")
            service = AdminUserService()

            if action in ("activate", "suspend", "deactivate"):
                service.lifecycle_action(
                    domain=domain,
                    user_id=user_id,
                    action=action,
                    admin_id=request.user.pk,
                )
            elif action == "verify":
                service.verify_user(
                    domain=domain, user_id=user_id, admin_id=request.user.pk
                )
            elif action == "reset_password":
                new_password = data.get("new_password")
                if not new_password:
                    return JsonResponse(
                        {"success": False, "error": "New password is required."},
                        status=400,
                    )
                service.reset_password(
                    domain=domain,
                    user_id=user_id,
                    new_password=new_password,
                    admin_id=request.user.pk,
                )
            elif action == "force_logout":
                service.force_logout(
                    domain=domain, user_id=user_id, admin_id=request.user.pk
                )
            else:
                return JsonResponse(
                    {"success": False, "error": f"Unknown action: {action}"}, status=400
                )

            return JsonResponse(
                {"success": True, "message": f"User successfully updated: {action}"}
            )
        except ValidationError as exc:
            msg = (
                exc.messages[0]
                if hasattr(exc, "messages") and exc.messages
                else str(exc)
            )
            return JsonResponse({"success": False, "error": msg}, status=400)
        except Exception as exc:
            logger.exception("User action failed")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)


class SuperAdminJobListView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/jobs/list.html"
    sidebar_active_key = "jobs"
    page_title = "Job & Vacancy Moderation"
    page_description = (
        "Review, approve, and manage postings across IT and Academic domains"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_type = self.request.GET.get("type", "it")
        search = self.request.GET.get("q", "")
        org_id = self.request.GET.get("org_id", "")
        if job_type == "faculty":
            qs = FacultyVacancy.objects.filter(is_deleted=False).select_related(
                "college"
            )
            if search:
                qs = qs.filter(title__icontains=search)
            if org_id:
                qs = qs.filter(college_id=org_id)
            context["postings"] = qs.order_by("-created_at")[:100]
        else:
            qs = JobPosting.objects.filter(is_deleted=False).select_related("company")
            if search:
                qs = qs.filter(title__icontains=search)
            if org_id:
                qs = qs.filter(company_id=org_id)
            context["postings"] = qs.order_by("-created_at")[:100]
        context["current_type"] = job_type
        context["current_search"] = search
        context["current_org_id"] = org_id
        context["it_stats"] = AdminJobService().platform_statistics()
        context["faculty_stats"] = AdminFacultyService().platform_statistics()
        return context


class SuperAdminJobDetailView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/jobs/detail.html"
    sidebar_active_key = "jobs"
    page_title = "Posting Detail & Audit"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job_type = self.request.GET.get("type", "it")
        job_id = kwargs.get("job_id")
        if job_type == "faculty":
            posting = get_object_or_404(FacultyVacancy, pk=job_id, is_deleted=False)
            apps = FacultyApplicationSelector().admin_list(vacancy_id=job_id)
            applications_data = AdminFacultyApplicationSerializer(apps, many=True).data
        else:
            posting = get_object_or_404(JobPosting, pk=job_id, is_deleted=False)
            apps = JobApplicationSelector().admin_list(job_posting_id=job_id)
            applications_data = AdminJobApplicationSerializer(apps, many=True).data
        context["posting"] = posting
        context["current_type"] = job_type
        context["applications"] = applications_data
        return context


class SuperAdminJobActionAPIView(SuperAdminPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            action = data.get("action")
            job_type = data.get("type", "it")
            remarks = data.get("remarks", "")
            job_id = kwargs.get("job_id")

            if job_type == "faculty":
                service = AdminFacultyService()
                posting = get_object_or_404(FacultyVacancy, pk=job_id, is_deleted=False)
            else:
                service = AdminJobService()
                posting = get_object_or_404(JobPosting, pk=job_id, is_deleted=False)

            if action == "approve":
                service.approve(posting, admin_id=request.user.pk, remarks=remarks)
            elif action == "reject":
                service.reject(posting, admin_id=request.user.pk, remarks=remarks)
            elif action == "close":
                service.close(posting, admin_id=request.user.pk)
            elif action == "archive":
                service.archive(posting, admin_id=request.user.pk)
            elif action == "featured":
                value = bool(data.get("value", True))
                service.set_featured(posting, admin_id=request.user.pk, value=value)
            else:
                return JsonResponse(
                    {"success": False, "error": f"Unknown action: {action}"}, status=400
                )

            return JsonResponse(
                {"success": True, "message": f"Posting successfully updated: {action}"}
            )
        except Exception as exc:
            logger.exception("Job action failed")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)


class SuperAdminApplicationListView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/applications/list.html"
    sidebar_active_key = "applications"
    page_title = "Platform Application Registry"
    page_description = "Monitor candidate pipeline and placement status across domains"

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "csv":
            domain = request.GET.get("domain", "it")
            service = AdminApplicationService()
            if domain == "faculty":
                content, content_type, filename = service.export_faculty_applications()
            else:
                content, content_type, filename = service.export_job_applications()
            resp = HttpResponse(content, content_type=content_type)
            resp["Content-Disposition"] = f'attachment; filename="{filename}"'
            return resp
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        domain = self.request.GET.get("domain", "it")
        search = self.request.GET.get("q", "")
        service = AdminApplicationService()
        if domain == "faculty":
            context["applications"] = service.faculty_selector.admin_list(
                search=search
            )[:100]
        else:
            context["applications"] = service.job_selector.admin_list(search=search)[
                :100
            ]
        context["current_domain"] = domain
        context["current_search"] = search
        return context


class SuperAdminBillingView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/billing/index.html"
    sidebar_active_key = "billing"
    page_title = "Financial Control & Guarantees"
    page_description = (
        "Placement invoices, fee collection, refunds, and guarantee claim resolution"
    )

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            action = data.get("action")
            target_type = data.get("target_type")
            target_id = data.get("target_id")

            if not target_type:
                if "invoice_id" in data:
                    target_type = "invoice"
                    target_id = data.get("invoice_id")
                elif "claim_id" in data:
                    target_type = "claim"
                    target_id = data.get("claim_id")

            if target_type == "invoice":
                service = AdminInvoiceService()
                invoice = get_object_or_404(Invoice, pk=target_id, is_deleted=False)
                if action == "cancel":
                    service.cancel_invoice(
                        invoice, admin_id=request.user.pk, notes=data.get("notes", "")
                    )
                elif action == "refund":
                    amount = data.get("amount")
                    reason = data.get("reason", "Admin Refund")
                    service.refund_invoice(
                        invoice, admin_id=request.user.pk, amount=amount, reason=reason
                    )
                elif action == "mark_paid":
                    service.mark_paid(
                        invoice, admin_id=request.user.pk, notes=data.get("notes", "")
                    )
                elif action == "mark_overdue":
                    service.mark_overdue(
                        invoice, admin_id=request.user.pk, notes=data.get("notes", "")
                    )
                elif action == "send_reminder":
                    # Record the reminder request / Create a notification entry (Future integration point)
                    from apps.admin_panel.services.admin_audit import record_admin_action
                    record_admin_action(
                        admin_id=request.user.pk,
                        event_type="admin.invoice.reminder_sent",
                        entity_type="billing_invoice",
                        entity_id=invoice.pk,
                        payload={"invoice_number": invoice.invoice_number, "method": "simulated"},
                    )
                    # For now, it just simulates sending.
            elif target_type == "claim":
                service = AdminGuaranteeService()
                claim = get_object_or_404(
                    GuaranteeClaim, pk=target_id, is_deleted=False
                )
                if action == "approve":
                    service.approve_claim(
                        claim,
                        admin_id=request.user.pk,
                        resolution=data.get("resolution", "replacement"),
                        review_notes=data.get("notes", ""),
                    )
                elif action == "reject":
                    service.reject_claim(
                        claim,
                        admin_id=request.user.pk,
                        review_notes=data.get("notes", ""),
                    )
                elif action == "resolve_claim":
                    service.resolve_claim(
                        claim,
                        admin_id=request.user.pk,
                        review_notes=data.get("notes", ""),
                    )
                elif action == "reject_claim":
                    service.reject_claim(
                        claim,
                        admin_id=request.user.pk,
                        review_notes=data.get("notes", ""),
                    )
            return JsonResponse(
                {"success": True, "message": "Operation completed successfully."}
            )
        except Exception as exc:
            logger.exception("Billing action failed")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get Filter Params
        q = self.request.GET.get("q", "").strip()
        domain = self.request.GET.get("domain", "")
        status = self.request.GET.get("status", "")
        payment_status = self.request.GET.get("payment_status", "")
        issued_from = self.request.GET.get("issued_from", "")
        issued_to = self.request.GET.get("issued_to", "")
        
        from django.utils.dateparse import parse_datetime
        issued_from_dt = parse_datetime(issued_from) if issued_from else None
        issued_to_dt = parse_datetime(issued_to) if issued_to else None

        inv_service = AdminInvoiceService()
        
        # We can pass domain filter to the financial summary if we want the KPIs to be domain-specific
        context["financials"] = inv_service.financial_summary(domain=domain if domain else None)
        
        from apps.invoices.selectors.invoice_selector import InvoiceSelector
        selector = InvoiceSelector()
        
        invoices_qs = selector.search(
            q=q if q else None,
            domain=domain if domain else None,
            status=status if status else None,
            payment_status=payment_status if payment_status else None,
            issued_from=issued_from_dt,
            issued_to=issued_to_dt,
        )
        
        # Add Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(invoices_qs, 50)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        
        context["invoices"] = page_obj
        context["claims"] = GuaranteeClaim.objects.filter(is_deleted=False).order_by("-created_at")[:50]
        
        # Pass back filters to template to keep state
        context["current_q"] = q
        context["current_domain"] = domain
        context["current_status"] = status
        context["current_payment_status"] = payment_status
        context["current_issued_from"] = issued_from
        context["current_issued_to"] = issued_to
        
        return context


class SuperAdminInvoiceView(SuperAdminPortalMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        invoice_id = kwargs.get("invoice_id")
        invoice = get_object_or_404(Invoice, pk=invoice_id, is_deleted=False)
        from apps.invoices.services.invoice_rendering_service import InvoiceRenderingService
        html = InvoiceRenderingService(invoice).render_html()
        return HttpResponse(html)

class SuperAdminInvoiceDownloadView(SuperAdminPortalMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        invoice_id = kwargs.get("invoice_id")
        invoice = get_object_or_404(Invoice, pk=invoice_id, is_deleted=False)
        from apps.invoices.services.invoice_rendering_service import InvoiceRenderingService
        pdf = InvoiceRenderingService(invoice).render_pdf()
        
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response

class SuperAdminInvoiceConfigurationView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/settings/invoice_configuration.html"
    sidebar_active_key = "invoice_config"
    page_title = "Global Invoice Configuration"
    page_description = "Configure the visual appearance, business details, and layout for all platform billing invoices."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.invoices.services.global_invoice_configuration_service import GlobalInvoiceConfigurationService
        from apps.invoices.forms.configuration_form import GlobalInvoiceConfigurationForm
        config = GlobalInvoiceConfigurationService.get_active_configuration()
        context["form"] = GlobalInvoiceConfigurationForm(instance=config)
        return context

    def post(self, request, *args, **kwargs):
        from apps.invoices.services.global_invoice_configuration_service import GlobalInvoiceConfigurationService
        success, result = GlobalInvoiceConfigurationService.update_configuration(
            request.POST, 
            updated_by_id=request.user.id
        )
        if success:
            return JsonResponse({"success": True, "message": "Global invoice configuration saved successfully."})
        return JsonResponse({"success": False, "errors": result}, status=400)


class SuperAdminInvoiceConfigurationPreviewAPIView(SuperAdminPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from apps.invoices.models.configuration import GlobalInvoiceConfiguration
        from django.template.loader import render_to_string
        from django.utils import timezone
        
        try:
            data = json.loads(request.body.decode("utf-8"))
            data.pop("csrfmiddlewaretoken", None)
            
            # Inject placeholders for preview if fields are empty but toggles are on
            if data.get("show_pan") and not data.get("pan"):
                data["pan"] = "[Your PAN Number]"
            if data.get("show_gstin") and not data.get("gstin"):
                data["gstin"] = "[Your GSTIN]"
            if data.get("show_phone") and not data.get("phone"):
                data["phone"] = "[Your Phone Number]"
            if data.get("show_email") and not data.get("email"):
                data["email"] = "[Your Email Address]"
            if data.get("show_website") and not data.get("website"):
                data["website"] = "[Your Website URL]"
            if data.get("show_terms") and not data.get("terms_conditions"):
                data["terms_conditions"] = "[Your Terms and Conditions will appear here]"
                
            config = GlobalInvoiceConfiguration(**data)
            
            # Simulate Recruitment Billing Calculation
            from decimal import Decimal, ROUND_HALF_UP
            
            pricing_method = config.pricing_method
            annual_ctc = Decimal('600000.00')
            
            if pricing_method == 'percentage_ctc':
                service_charge = Decimal(str(config.service_charge_percentage or 0))
                taxable = (annual_ctc * service_charge / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                taxable = Decimal(str(config.fixed_recruitment_fee or 0))
                
            total_tax = Decimal('0.00')
            cgst = Decimal('0.00')
            sgst = Decimal('0.00')
            igst = Decimal('0.00')
            
            gst_percentage = Decimal(str(config.gst_percentage or 0))
            if config.gst_enabled and gst_percentage > 0:
                total_tax = (taxable * gst_percentage / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if config.tax_calculation_mode == 'cgst_sgst':
                    cgst = (total_tax / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    sgst = total_tax - cgst
                else:
                    igst = total_tax
                    
            grand_total = taxable + total_tax
            
            class DummyInvoice:
                invoice_number = "EDU-INV-2026-000001"
                created_at = timezone.now()
                issued_at = timezone.now()
                due_at = timezone.now()
                status = "paid"
                bill_to_name_snapshot = "Demo Organization"
                pdf_metadata = {"billing_address": "123 Demo St.\nCity, State 12345", "gstin": "29ABCDE1234F1Z5"}
                currency = config.currency
                subtotal = taxable
                tax_amount = total_tax
                total_amount = grand_total
                amount_paid = grand_total
                paid_at = timezone.now()
                
                # Snapshot fields for Recruitment Billing
                candidate_name = "Demo Candidate"
                candidate_job_title = "Assistant Professor - Computer Science"
                candidate_annual_ctc = annual_ctc
                pricing_method_snapshot = config.pricing_method
                service_charge_percentage_snapshot = config.service_charge_percentage
                cgst_amount = cgst
                sgst_amount = sgst
                igst_amount = igst
                taxable_amount = taxable
            
            class DummyLineItem:
                description = "Recruitment Service Fee – Demo Candidate"
                quantity = Decimal('1')
                unit_price = taxable
                line_total = taxable
            
            class DummyPayment:
                def get_payment_method_display(self):
                    return "Credit Card"
                reference_number = "TXN123456789"
                
            class DummyQuerySet:
                def __init__(self, items):
                    self.items = items
                def exists(self):
                    return len(self.items) > 0
                def first(self):
                    return self.items[0] if self.items else None
                def all(self):
                    return self.items
                
            context = {
                "invoice": DummyInvoice(),
                "line_items": [DummyLineItem()],
                "payments": DummyQuerySet([DummyPayment()]),
                "config": config,
            }
            
            html = render_to_string("invoices/invoice_template.html", context)
            return HttpResponse(html)
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=500)


class SuperAdminOrganizationListView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/organizations/list.html"
    sidebar_active_key = "organizations"
    page_title = "Organizations"
    page_description = "Manage all registered IT Companies and Academic Institutions from a single dashboard."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        org_type = self.request.GET.get("type", "company")
        search = self.request.GET.get("q", "")
        status_filter = self.request.GET.get("status", "")
        
        if org_type == "college":
            qs = College.objects.filter(is_deleted=False).prefetch_related("members")
            if search:
                qs = qs.filter(name__icontains=search)
            if status_filter == "active":
                qs = qs.filter(is_active=True)
            elif status_filter == "deactivated":
                qs = qs.filter(is_active=False)
            context["organizations"] = qs.order_by("-created_at")[:100]
        else:
            qs = Company.objects.filter(is_deleted=False).prefetch_related("members")
            if search:
                qs = qs.filter(name__icontains=search)
            if status_filter == "active":
                qs = qs.filter(is_active=True)
            elif status_filter == "deactivated":
                qs = qs.filter(is_active=False)
            context["organizations"] = qs.order_by("-created_at")[:100]
            
        context["current_type"] = org_type
        context["current_search"] = search
        context["current_status"] = status_filter
        return context


class SuperAdminOrganizationActionAPIView(SuperAdminPortalMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            action = data.get("action")
            org_type = data.get("type", "company")
            remarks = data.get("remarks", "")
            org_id = kwargs.get("org_id")

            if org_type == "college":
                service = AdminCollegeService()
                org = get_object_or_404(College, pk=org_id, is_deleted=False)
            else:
                service = AdminCompanyService()
                org = get_object_or_404(Company, pk=org_id, is_deleted=False)

            if action == "deactivate":
                service.deactivate(org, admin_id=request.user.pk, remarks=remarks)
            else:
                return JsonResponse(
                    {"success": False, "error": f"Unknown action: {action}"}, status=400
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Organization successfully updated: {action}",
                }
            )
        except Exception as exc:
            return JsonResponse({"success": False, "error": str(exc)}, status=500)


class SuperAdminAnalyticsView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/analytics/index.html"
    sidebar_active_key = "analytics"
    page_title = "Enterprise Analytics & Intelligence"
    page_description = (
        "Cross-domain conversion funnels, placement trends, and revenue growth"
    )

    def get(self, request, *args, **kwargs):
        export_table = request.GET.get("export_table")
        if export_table:
            filters = {}
            domain = self.request.GET.get("domain")
            if domain:
                filters["domain"] = domain
                
            search = self.request.GET.get("search")
            if search:
                filters["search"] = search
                
            org_id = self.request.GET.get("org_id")
            if org_id:
                filters["org_id"] = org_id
                
            invoice_status = self.request.GET.get("invoice_status")
            if invoice_status:
                filters["invoice_status"] = invoice_status
                
            payment_status = self.request.GET.get("payment_status")
            if payment_status:
                filters["payment_status"] = payment_status
                
            date_range = self.request.GET.get("date_range")
            if date_range:
                filters["date_range"] = date_range

            service = AdminAnalyticsService()
            enterprise_data = service.enterprise_analytics_overview(**filters)
            
            import csv
            from io import StringIO
            from django.http import HttpResponse
            
            output = StringIO()
            writer = csv.writer(output)
            
            if export_table == "placements":
                writer.writerow(["Candidate Name", "Domain", "Recruiter / Institution", "Job Title", "Salary / CTC", "Joining Date", "Current Status", "Invoice Status"])
                for row in enterprise_data.get("placement_analytics", {}).get("results", []):
                    writer.writerow([row.get("candidate_name"), row.get("domain"), row.get("recruiter"), row.get("job_title"), row.get("salary"), row.get("joining_date"), row.get("status"), row.get("invoice_status")])
                filename = "Placement_Analytics.csv"
            elif export_table == "revenue":
                writer.writerow(["Organization Name", "Domain", "Candidates Hired", "Total Placement Fee", "Total GST", "Total Invoice Amount", "Total Paid Amount", "Pending Balance", "Last Payment Date"])
                for row in enterprise_data.get("revenue_analytics", []):
                    writer.writerow([row.get("organization_name"), row.get("domain"), row.get("candidates_hired"), row.get("total_fee"), row.get("total_gst"), row.get("total_invoice"), row.get("total_paid"), row.get("pending_amount"), row.get("last_payment_date")])
                filename = "Institutional_Revenue.csv"
            elif export_table == "top_institutions":
                writer.writerow(["Rank", "Organization Name", "Domain", "Hires", "Total Revenue", "Total Paid", "Outstanding Balance"])
                for row in enterprise_data.get("top_revenue_institutions", []):
                    writer.writerow([row.get("rank"), row.get("organization_name"), row.get("domain"), row.get("candidates_hired"), row.get("total_revenue"), row.get("total_paid"), row.get("outstanding_balance")])
                filename = "Top_Institutions.csv"
            elif export_table == "recent_placements":
                writer.writerow(["Candidate Name", "Domain", "Recruiter / Institution", "Designation", "CTC", "Joined On", "Payment Status"])
                for row in enterprise_data.get("recent_placements", []):
                    writer.writerow([row.get("candidate_name"), row.get("domain"), row.get("recruiter"), row.get("designation"), row.get("salary"), row.get("joined_on"), row.get("payment_status")])
                filename = "Recent_Placements.csv"
            else:
                return super().get(request, *args, **kwargs)

            response = HttpResponse(output.getvalue(), content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
            
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        filters = {}
        domain = self.request.GET.get("domain")
        if domain:
            filters["domain"] = domain
            
        search = self.request.GET.get("search")
        if search:
            filters["search"] = search
            
        org_id = self.request.GET.get("org_id")
        if org_id:
            filters["org_id"] = org_id
            
        invoice_status = self.request.GET.get("invoice_status")
        if invoice_status:
            filters["invoice_status"] = invoice_status
            
        payment_status = self.request.GET.get("payment_status")
        if payment_status:
            filters["payment_status"] = payment_status
            
        date_range = self.request.GET.get("date_range")
        if date_range:
            filters["date_range"] = date_range

        service = AdminAnalyticsService()
        context["enterprise_data"] = service.enterprise_analytics_overview(**filters)
        context["current_filters"] = filters
        
        return context


class SuperAdminReportsView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/reports/index.html"
    sidebar_active_key = "reports"
    page_title = "Reporting & Data Export"
    page_description = (
        "Generate and export regulatory, financial, and operational reports"
    )

    def get(self, request, *args, **kwargs):
        report_type = request.GET.get("export")
        if report_type:
            export_as = request.GET.get("format", "json")
            service = AdminReportService()
            content, content_type, filename = service.export_report(
                report_type, export_as=export_as
            )
            resp = HttpResponse(content, content_type=content_type)
            resp["Content-Disposition"] = f'attachment; filename="{filename}"'
            return resp
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = AdminReportService()
        context["report_types"] = [
            {
                "id": "total_users",
                "name": "Total Users Report",
                "desc": "Download all registered users across the platform.",
            },
            {
                "id": "it_placements",
                "name": "IT Domain Placements Report",
                "desc": "Download all successfully joined candidates from the IT Recruitment domain.",
            },
            {
                "id": "faculty_placements",
                "name": "Faculty Domain Placements Report",
                "desc": "Download all successfully joined candidates from the Faculty Recruitment domain.",
            },
            {
                "id": "refund_claims",
                "name": "Refund Claim Success Report",
                "desc": "Download all guarantee claim and refund records.",
            },
        ]
        return context


class SuperAdminSettingsView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/settings/index.html"
    sidebar_active_key = "settings"
    page_title = "Platform Configuration"
    page_description = (
        "Global system settings, placement guarantee thresholds, and upload limits"
    )

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body.decode("utf-8"))
            key = data.get("key")
            value = data.get("value")
            service = AdminConfigService()
            service.update_setting(
                key,
                value=value,
                admin_id=request.user.pk,
                description=data.get("description", ""),
            )
            return JsonResponse(
                {"success": True, "message": f"Setting {key} successfully updated."}
            )
        except Exception as exc:
            logger.exception("Update setting failed")
            return JsonResponse({"success": False, "error": str(exc)}, status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = AdminConfigService()
        context["settings_list"] = service.list_settings()
        return context





class SuperAdminNotificationsView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/notifications/index.html"
    sidebar_active_key = "notifications"
    page_title = "System Notifications"
    page_description = (
        "Platform alerts, system health warnings, and background job notifications"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["notifications"] = []
        return context


class SuperAdminSupportView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/support/index.html"
    sidebar_active_key = "support"
    page_title = "Support & Escalations"
    page_description = (
        "Help desk escalations, dispute resolutions, and customer support inquiries"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tickets"] = []
        return context


class SuperAdminGuaranteeClaimsView(SuperAdminPortalMixin, TemplateView):
    template_name = "super_admin/billing/claims_list.html"
    sidebar_active_key = "billing_claims"
    page_title = "Guarantee Claims & Refunds"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.guarantee_claims.models.claim import GuaranteeClaim
        from django.db.models import Count, Q
        
        from apps.guarantee_claims.services.query_service import GuaranteeClaimQueryService
        
        qs = GuaranteeClaimQueryService.get_operational_claims()
        
        # Filtering
        domain_filter = self.request.GET.get('domain')
        status_filter = self.request.GET.get('status')
        if domain_filter:
            qs = qs.filter(domain=domain_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
            
        context["stats"] = GuaranteeClaim.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status__in=['submitted', 'under_review', 'more_information_required'])),
            approved=Count('id', filter=Q(status='approved')),
            refund_processing=Count('id', filter=Q(status='refund_processing')),
            resolved=Count('id', filter=Q(status='resolved')),
            rejected=Count('id', filter=Q(status='rejected'))
        )

        from apps.guarantee_claims.services.action_service import GuaranteeClaimActionService
        
        # Attach dynamic actions to each claim
        claims = list(qs)
        for claim in claims:
            claim.available_actions = GuaranteeClaimActionService.get_available_actions(claim)

        context["claims"] = claims
        context["current_domain"] = domain_filter
        context["current_status"] = status_filter
        return context

from django.views import View
from django.http import JsonResponse
import json

class SuperAdminGuaranteeClaimActionView(SuperAdminPortalMixin, View):
    def post(self, request, claim_id, *args, **kwargs):
        try:
            data = json.loads(request.body)
            action = data.get("action")
            notes = data.get("notes", "Action performed via Super Admin Dashboard")
            
            from apps.guarantee_claims.models.claim import GuaranteeClaim
            from apps.guarantee_claims.services.workflow_service import GuaranteeClaimWorkflowService
            from apps.guarantee_claims.services.refund_service import GuaranteeRefundService
            from apps.guarantee_claims.constants.enums import ClaimStatus
            from decimal import Decimal
            
            claim = GuaranteeClaim.objects.get(pk=claim_id)
            
            if action == "review":
                GuaranteeClaimWorkflowService.change_status(claim, ClaimStatus.UNDER_REVIEW, changed_by_id=request.user.id, notes=notes)
            elif action == "reject":
                GuaranteeClaimWorkflowService.change_status(claim, ClaimStatus.REJECTED, changed_by_id=request.user.id, notes=notes)
            elif action == "approve_refund":
                # By default, approving full refund based on invoice
                from apps.invoices.models import Invoice
                invoice = Invoice.objects.filter(pk=claim.invoice_id).first()
                if not invoice:
                    return JsonResponse({"success": False, "error": "No associated invoice found."})
                GuaranteeRefundService.process_refund_approval(claim, invoice.total_amount, admin_id=request.user.id, notes=notes)
            elif action == "mark_refunded":
                from apps.guarantee_claims.models.refund import GuaranteeRefund
                refund = GuaranteeRefund.objects.filter(claim_id=claim.pk).first()
                if refund:
                    GuaranteeRefundService.record_manual_refund_transaction(
                        refund, transaction_reference=data.get('transaction_ref', 'MANUAL-WEB'), admin_id=request.user.id, notes=notes
                    )
            elif action == "resolve":
                GuaranteeClaimWorkflowService.change_status(claim, ClaimStatus.RESOLVED, changed_by_id=request.user.id, notes=notes)
            else:
                return JsonResponse({"success": False, "error": "Invalid action."})
                
            return JsonResponse({"success": True, "message": f"Claim updated successfully to {claim.get_status_display()}"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
