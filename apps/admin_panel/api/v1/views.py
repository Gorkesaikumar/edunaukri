from drf_spectacular.utils import extend_schema

from drf_spectacular.utils import extend_schema
from django.http import HttpResponse
from rest_framework import permissions, status
from apps.authentication.permissions.throttles import DashboardAPIThrottle, ReportsAPIThrottle

from apps.admin_panel.api.v1.serializers import (
    AdminClaimApproveSerializer,
    AdminClaimNotesSerializer,
    AdminCompanySummarySerializer,
    AdminCollegeSummarySerializer,
    AdminRecruiterSummarySerializer,
    AdminJobApplicationSerializer,
    AdminFacultyApplicationSerializer,
    AdminFeatureSerializer,
    AdminPasswordResetSerializer,
    AdminRefundSerializer,
    AdminRemarksSerializer,
    PlatformSettingSerializer,
    PlatformSettingUpdateSerializer,
    UserLifecycleSerializer,
)
from apps.admin_panel.permissions.admin_permissions import IsEnterpriseAdmin
from apps.admin_panel.services.admin_analytics_service import AdminAnalyticsService
from apps.admin_panel.services.admin_application_service import AdminApplicationService
from apps.admin_panel.services.admin_audit_service import AdminAuditService
from apps.admin_panel.services.admin_billing_service import (
    AdminFeeScheduleService,
    AdminGuaranteeService,
    AdminInvoiceService,
)
from apps.admin_panel.services.admin_college_service import AdminCollegeService
from apps.admin_panel.services.admin_company_service import AdminCompanyService
from apps.admin_panel.services.admin_config_service import AdminConfigService
from apps.admin_panel.services.admin_dashboard_service import AdminDashboardService
from apps.admin_panel.services.admin_faculty_service import AdminFacultyService
from apps.admin_panel.services.admin_job_service import AdminJobService
from apps.admin_panel.services.admin_report_service import (
    AdminReportService,
    VALID_REPORT_TYPES,
)
from apps.admin_panel.services.admin_user_service import AdminUserService
from apps.admin_panel.validators.admin_validators import (
    validate_report_type,
    validate_user_domain,
)
from apps.applications.api.v1.serializers import (
    FacultyApplicationSerializer,
    FacultyApplicationStatusHistorySerializer,
    FacultyApplicationStatusSerializer,
    JobApplicationSerializer,
    JobApplicationStatusHistorySerializer,
    JobApplicationStatusSerializer,
)
from apps.applications.selectors.application_selector import (
    FacultyApplicationSelector,
    JobApplicationSelector,
)
from apps.audit.api.v1.serializers import AuditEventSerializer
from apps.billing.api.v1.serializers import (
    FeeScheduleCreateSerializer,
    FeeScheduleSerializer,
    PlacementFeeSerializer,
)
from apps.billing.selectors.fee_selector import (
    FeeScheduleSelector,
    PlacementFeeSelector,
)
from apps.colleges.api.v1.serializers import InstitutionSerializer
from apps.colleges.selectors.college_selector import CollegeSelector
from apps.companies.api.v1.serializers import CompanySerializer
from apps.companies.selectors.company_selector import CompanySelector
from apps.core.pagination import StandardResultsSetPagination, paginate_envelope
from apps.core.views.base import EnvelopeAPIView
from apps.faculty.api.v1.serializers import FacultyVacancySerializer
from apps.faculty.selectors.vacancy_selector import FacultyVacancySelector
from apps.guarantee_claims.api.v1.serializers import GuaranteeClaimSerializer
from apps.guarantee_claims.selectors.claim_selector import GuaranteeClaimSelector
from apps.invoices.api.v1.serializers import InvoiceSerializer
from apps.invoices.selectors.invoice_selector import InvoiceSelector
from apps.jobs.api.v1.serializers import JobPostingSerializer
from apps.jobs.selectors.job_selector import JobPostingSelector


class _AdminView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEnterpriseAdmin]
    throttle_classes = [DashboardAPIThrottle, ReportsAPIThrottle]


class AdminDashboardView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AdminDashboardService().summary())


class AdminDashboardActivitiesView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        return self.success_response(
            AdminDashboardService().recent_activities(limit=limit)
        )


class AdminDashboardHealthView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AdminDashboardService().system_health())


class AdminUserListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        users = AdminUserService().list_users(
            domain=request.query_params.get("domain"),
            is_active=(
                request.query_params.get("is_active", "").lower() in ("1", "true")
                if request.query_params.get("is_active") is not None
                else None
            ),
            account_status=request.query_params.get("account_status"),
            search=request.query_params.get("search"),
        )
        return self.success_response(users)


class AdminUserDetailView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, domain, user_id):
        validate_user_domain(domain)
        user = AdminUserService().get_user(domain=domain, user_id=user_id)
        if not user:
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        return self.success_response(user)


class AdminUserLifecycleView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, domain, user_id):
        validate_user_domain(domain)
        if not AdminUserService().user_exists(domain, user_id):
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        serializer = UserLifecycleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AdminUserService().lifecycle_action(
            domain=domain,
            user_id=user_id,
            action=serializer.validated_data["action"],
            admin_id=request.user.pk,
        )
        user = AdminUserService().get_user(domain=domain, user_id=user_id)
        return self.success_response(user)


class AdminUserVerifyView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, domain, user_id):
        validate_user_domain(domain)
        if not AdminUserService().user_exists(domain, user_id):
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        AdminUserService().verify_user(
            domain=domain, user_id=user_id, admin_id=request.user.pk
        )
        return self.success_response(
            AdminUserService().get_user(domain=domain, user_id=user_id)
        )


class AdminUserResetPasswordView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, domain, user_id):
        validate_user_domain(domain)
        if not AdminUserService().user_exists(domain, user_id):
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        serializer = AdminPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AdminUserService().reset_password(
            domain=domain,
            user_id=user_id,
            new_password=serializer.validated_data["new_password"],
            admin_id=request.user.pk,
        )
        return self.success_response({"message": "Password reset successfully."})


class AdminUserForceLogoutView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, domain, user_id):
        validate_user_domain(domain)
        if not AdminUserService().user_exists(domain, user_id):
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        AdminUserService().force_logout(
            domain=domain, user_id=user_id, admin_id=request.user.pk
        )
        return self.success_response({"message": "User sessions revoked."})


class AdminUserLoginHistoryView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, domain, user_id):
        validate_user_domain(domain)
        if not AdminUserService().user_exists(domain, user_id):
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        limit = int(request.query_params.get("limit", 50))
        return self.success_response(
            AdminUserService().login_history(
                domain=domain, user_id=user_id, limit=limit
            )
        )


class AdminUserActivityView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, domain, user_id):
        validate_user_domain(domain)
        if not AdminUserService().user_exists(domain, user_id):
            return self.error_response("NOT_FOUND", "User not found.", status=404)
        limit = int(request.query_params.get("limit", 50))
        return self.success_response(
            AdminUserService().user_activity(
                domain=domain, user_id=user_id, limit=limit
            )
        )


class AdminCompanyListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            is_active = is_active.lower() in ("1", "true", "yes")
        companies = CompanySelector().admin_list(
            status=request.query_params.get("status"),
            is_active=is_active,
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, companies, CompanySerializer)


class AdminCompanyActionView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, company_id, action):
        company = CompanySelector().get_or_none(company_id)
        if not company:
            return self.error_response("NOT_FOUND", "Company not found.", status=404)
        serializer = AdminRemarksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data.get("remarks", "")
        service = AdminCompanyService()
        if action == "activate":
            company = service.activate(
                company, admin_id=request.user.pk, remarks=remarks
            )
        elif action == "deactivate":
            company = service.deactivate(
                company, admin_id=request.user.pk, remarks=remarks
            )
        else:
            return self.error_response(
                "VALIDATION_ERROR", "Invalid action.", status=400
            )
        return self.success_response(CompanySerializer(company).data)


class AdminCollegeListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        colleges = CollegeSelector().admin_list(
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, colleges, InstitutionSerializer)


class AdminCollegeActionView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id, action):
        college = CollegeSelector().get_or_none(college_id)
        if not college:
            return self.error_response("NOT_FOUND", "College not found.", status=404)
        serializer = AdminRemarksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        remarks = serializer.validated_data.get("remarks", "")
        service = AdminCollegeService()
        if action == "activate":
            college = service.activate(
                college, admin_id=request.user.pk, remarks=remarks
            )
        elif action == "deactivate":
            college = service.deactivate(
                college, admin_id=request.user.pk, remarks=remarks
            )
        else:
            return self.error_response(
                "VALIDATION_ERROR", "Invalid action.", status=400
            )
        return self.success_response(InstitutionSerializer(college).data)


class AdminJobListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        jobs = JobPostingSelector().admin_list(
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, jobs, JobPostingSerializer)


class AdminJobStatisticsView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AdminJobService().platform_statistics())


class AdminJobDetailView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, job_id):
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        data = JobPostingSerializer(job).data
        if job.company:
            data["company"] = AdminCompanySummarySerializer(job.company).data
        if job.posted_by:
            data["posted_by"] = AdminRecruiterSummarySerializer(job.posted_by).data
        return self.success_response(data)


class AdminJobActionView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, job_id, action):
        job = JobPostingSelector().get_or_none(job_id)
        if not job:
            return self.error_response("NOT_FOUND", "Job not found.", status=404)
        service = AdminJobService()
        remarks = ""
        if action in ("approve", "reject"):
            serializer = AdminRemarksSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            remarks = serializer.validated_data.get("remarks", "")
        if action == "approve":
            job = service.approve(job, admin_id=request.user.pk, remarks=remarks)
        elif action == "reject":
            job = service.reject(job, admin_id=request.user.pk, remarks=remarks)
        elif action == "close":
            job = service.close(job, admin_id=request.user.pk)
        elif action == "archive":
            job = service.archive(job, admin_id=request.user.pk)
        elif action == "feature":
            serializer = AdminFeatureSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            job = service.set_featured(
                job,
                admin_id=request.user.pk,
                value=serializer.validated_data["is_featured"],
            )
        else:
            return self.error_response(
                "VALIDATION_ERROR", "Invalid action.", status=400
            )
        return self.success_response(JobPostingSerializer(job).data)


class AdminVacancyListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        vacancies = FacultyVacancySelector().admin_list(
            status=request.query_params.get("status"),
            search=request.query_params.get("search"),
        )
        return paginate_envelope(request, vacancies, FacultyVacancySerializer)


class AdminVacancyStatisticsView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AdminFacultyService().platform_statistics())


class AdminVacancyDetailView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, vacancy_id):
        vacancy = FacultyVacancySelector().get_or_none(vacancy_id)
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        data = FacultyVacancySerializer(vacancy).data
        if vacancy.college:
            data["college"] = AdminCollegeSummarySerializer(vacancy.college).data
        if vacancy.posted_by:
            data["posted_by"] = AdminRecruiterSummarySerializer(vacancy.posted_by).data
        return self.success_response(data)


class AdminVacancyActionView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, vacancy_id, action):
        vacancy = FacultyVacancySelector().get_or_none(vacancy_id)
        if not vacancy:
            return self.error_response("NOT_FOUND", "Vacancy not found.", status=404)
        service = AdminFacultyService()
        remarks = ""
        if action in ("approve", "reject"):
            serializer = AdminRemarksSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            remarks = serializer.validated_data.get("remarks", "")
        if action == "approve":
            vacancy = service.approve(
                vacancy, admin_id=request.user.pk, remarks=remarks
            )
        elif action == "reject":
            vacancy = service.reject(vacancy, admin_id=request.user.pk, remarks=remarks)
        elif action == "close":
            vacancy = service.close(vacancy, admin_id=request.user.pk)
        elif action == "archive":
            vacancy = service.archive(vacancy, admin_id=request.user.pk)
        elif action == "feature":
            serializer = AdminFeatureSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            vacancy = service.set_featured(
                vacancy,
                admin_id=request.user.pk,
                value=serializer.validated_data["is_featured"],
            )
        else:
            return self.error_response(
                "VALIDATION_ERROR", "Invalid action.", status=400
            )
        return self.success_response(FacultyVacancySerializer(vacancy).data)


class AdminJobApplicationListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        apps = JobApplicationSelector().admin_list(
            status=request.query_params.get("status"),
            job_posting_id=request.query_params.get("job_posting_id"),
        )
        return paginate_envelope(request, apps, AdminJobApplicationSerializer)


class AdminJobApplicationExportView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        content, content_type, filename = (
            AdminApplicationService().export_job_applications(
                status=request.query_params.get("status"),
                job_posting_id=request.query_params.get("job_posting_id"),
            )
        )
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AdminJobApplicationDetailView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        return self.success_response(AdminJobApplicationSerializer(application).data)


class AdminJobApplicationStatusView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        serializer = JobApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        service = AdminApplicationService()
        application = service.update_job_status(
            application,
            status=serializer.validated_data["status"],
            notes=serializer.validated_data.get("notes", ""),
            actor=request.user,
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        service.record_status_override(
            admin_id=request.user.pk,
            domain="it",
            application_id=application.pk,
            status=serializer.validated_data["status"],
        )
        return self.success_response(AdminJobApplicationSerializer(application).data)


class AdminJobApplicationHistoryView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = JobApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        history = AdminApplicationService().job_history(application)
        return self.success_response(
            JobApplicationStatusHistorySerializer(history, many=True).data
        )


class AdminFacultyApplicationListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        apps = FacultyApplicationSelector().admin_list(
            status=request.query_params.get("status"),
            vacancy_id=request.query_params.get("vacancy_id"),
        )
        return paginate_envelope(request, apps, AdminFacultyApplicationSerializer)


class AdminFacultyApplicationExportView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        content, content_type, filename = (
            AdminApplicationService().export_faculty_applications(
                status=request.query_params.get("status"),
                vacancy_id=request.query_params.get("vacancy_id"),
            )
        )
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AdminFacultyApplicationDetailView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        return self.success_response(
            AdminFacultyApplicationSerializer(application).data
        )


class AdminFacultyApplicationStatusView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, application_id):
        serializer = FacultyApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        service = AdminApplicationService()
        application = service.update_faculty_status(
            application,
            status=serializer.validated_data["status"],
            notes=serializer.validated_data.get("notes", ""),
            actor=request.user,
            rejection_reason=serializer.validated_data.get("rejection_reason", ""),
        )
        service.record_status_override(
            admin_id=request.user.pk,
            domain="faculty",
            application_id=application.pk,
            status=serializer.validated_data["status"],
        )
        return self.success_response(
            AdminFacultyApplicationSerializer(application).data
        )


class AdminFacultyApplicationHistoryView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, application_id):
        application = FacultyApplicationSelector().get_active(application_id)
        if not application:
            return self.error_response(
                "NOT_FOUND", "Application not found.", status=404
            )
        history = AdminApplicationService().faculty_history(application)
        return self.success_response(
            FacultyApplicationStatusHistorySerializer(history, many=True).data
        )


class AdminInvoiceListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        invoices = InvoiceSelector().search(
            domain=request.query_params.get("domain"),
            status=request.query_params.get("status"),
            payment_status=request.query_params.get("payment_status"),
            q=request.query_params.get("q"),
        )
        return paginate_envelope(request, invoices, InvoiceSerializer)


class AdminInvoiceFinancialSummaryView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        summary = AdminInvoiceService().financial_summary(
            domain=request.query_params.get("domain")
        )
        return self.success_response(summary)


class AdminInvoiceCancelView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, invoice_id):
        invoice = InvoiceSelector().get_active(invoice_id)
        if not invoice:
            return self.error_response("NOT_FOUND", "Invoice not found.", status=404)
        serializer = AdminRemarksSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = AdminInvoiceService().cancel_invoice(
            invoice,
            admin_id=request.user.pk,
            notes=serializer.validated_data.get("remarks", ""),
        )
        return self.success_response(InvoiceSerializer(invoice).data)


class AdminInvoiceRefundView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, invoice_id):
        invoice = InvoiceSelector().get_active(invoice_id)
        if not invoice:
            return self.error_response("NOT_FOUND", "Invoice not found.", status=404)
        serializer = AdminRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AdminInvoiceService().refund_invoice(
            invoice, admin_id=request.user.pk, **serializer.validated_data
        )
        invoice.refresh_from_db()
        return self.success_response(
            InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED
        )


class AdminGuaranteeClaimListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        claims = GuaranteeClaimSelector().list_by_domain(
            request.query_params.get("domain"),
            status=request.query_params.get("status"),
        )
        return paginate_envelope(request, claims, GuaranteeClaimSerializer)


class AdminGuaranteeClaimActionView(_AdminView):
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, claim_id, action):
        claim = GuaranteeClaimSelector().get_active(claim_id)
        if not claim:
            return self.error_response("NOT_FOUND", "Claim not found.", status=404)
        service = AdminGuaranteeService()
        if action == "approve":
            serializer = AdminClaimApproveSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            claim = service.approve_claim(
                claim, admin_id=request.user.pk, **serializer.validated_data
            )
        elif action == "reject":
            serializer = AdminClaimNotesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            claim = service.reject_claim(
                claim,
                admin_id=request.user.pk,
                review_notes=serializer.validated_data.get("review_notes", ""),
            )
        elif action == "resolve":
            serializer = AdminClaimNotesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            claim = service.resolve_claim(
                claim,
                admin_id=request.user.pk,
                review_notes=serializer.validated_data.get("review_notes", ""),
            )
        else:
            return self.error_response(
                "VALIDATION_ERROR", "Invalid action.", status=400
            )
        return self.success_response(GuaranteeClaimSerializer(claim).data)


class AdminFeeScheduleListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        schedules = FeeScheduleSelector().list_by_domain(
            request.query_params.get("domain")
        )
        return self.success_response(FeeScheduleSerializer(schedules, many=True).data)

    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = FeeScheduleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = AdminFeeScheduleService().create_schedule(
            data=serializer.validated_data,
            admin_id=request.user.pk,
        )
        return self.success_response(
            FeeScheduleSerializer(schedule).data, status=status.HTTP_201_CREATED
        )


class AdminPlacementFeeListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        fees = PlacementFeeSelector().list_by_domain(request.query_params.get("domain"))
        return self.success_response(PlacementFeeSerializer(fees, many=True).data)


class AdminAnalyticsView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(AdminAnalyticsService().overview())


class AdminReportView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, report_type):
        validate_report_type(report_type)
        return self.success_response(AdminReportService().get_report(report_type))


class AdminReportExportView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, report_type):
        validate_report_type(report_type)
        content, content_type, filename = AdminReportService().export_report(
            report_type, export_as=request.query_params.get("export_as", "csv")
        )
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AdminAuditLogListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        queryset = AdminAuditService().list_events(
            domain=request.query_params.get("domain"),
            event_type=request.query_params.get("event_type"),
            entity_type=request.query_params.get("entity_type"),
            entity_id=request.query_params.get("entity_id"),
            actor_id=request.query_params.get("actor_id"),
            occurred_after=request.query_params.get("occurred_after"),
            occurred_before=request.query_params.get("occurred_before"),
            q=request.query_params.get("q"),
        )
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditEventSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminAuditLogExportView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        content, content_type, filename = AdminAuditService().export_events(
            export_as=request.query_params.get("export_as", "csv"),
            domain=request.query_params.get("domain"),
            event_type=request.query_params.get("event_type"),
            entity_id=request.query_params.get("entity_id"),
            actor_id=request.query_params.get("actor_id"),
            occurred_after=request.query_params.get("occurred_after"),
            occurred_before=request.query_params.get("occurred_before"),
        )
        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class AdminSettingsListView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request):
        settings = AdminConfigService().list_settings(
            category=request.query_params.get("category")
        )
        return self.success_response(
            PlatformSettingSerializer(settings, many=True).data
        )


class AdminSettingDetailView(_AdminView):
    @extend_schema(responses={200: dict})
    def get(self, request, setting_key):
        setting = AdminConfigService().get_setting(setting_key)
        if not setting:
            return self.error_response("NOT_FOUND", "Setting not found.", status=404)
        return self.success_response(PlatformSettingSerializer(setting).data)

    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, setting_key):
        setting = AdminConfigService().get_setting(setting_key)
        if not setting:
            return self.error_response("NOT_FOUND", "Setting not found.", status=404)
        serializer = PlatformSettingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        setting = AdminConfigService().update_setting(
            setting_key,
            value=serializer.validated_data["value"],
            admin_id=request.user.pk,
            description=serializer.validated_data.get("description", ""),
        )
        return self.success_response(PlatformSettingSerializer(setting).data)
