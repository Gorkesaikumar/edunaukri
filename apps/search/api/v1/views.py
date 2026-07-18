from drf_spectacular.utils import extend_schema
from rest_framework import permissions

from apps.admin_panel.permissions.admin_permissions import IsEnterpriseAdmin
from apps.core.views.base import EnvelopeAPIView
from apps.search.api.v1.serializers import (
    ApplicationSearchResultSerializer,
    CollegeSearchResultSerializer,
    CompanySearchResultSerializer,
    GuaranteeSearchResultSerializer,
    InvoiceSearchResultSerializer,
    JobSearchResultSerializer,
    JobSeekerSearchResultSerializer,
    ProfessorSearchResultSerializer,
    RecruiterSearchResultSerializer,
    VacancySearchResultSerializer,
)
from apps.search.constants.enums import SearchResource
from apps.search.permissions.search_permissions import IsAdminOrCollegeUser
from apps.authentication.permissions.throttles import BruteForceIPThrottle
from apps.search.permissions.throttles import SearchAnonThrottle, SearchEndpointThrottle
from apps.search.services.pagination_service import PaginationService
from apps.search.services.search_service import SearchService


class BaseSearchView(EnvelopeAPIView):
    """Reusable search view — parses params, delegates to SearchService, paginates results."""

    resource: str = ""
    serializer_class = None
    throttle_classes = [BruteForceIPThrottle, SearchAnonThrottle, SearchEndpointThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        from django.core.exceptions import PermissionDenied, ValidationError

        from apps.search.validators.search_validators import SearchValidator

        try:
            if request.query_params.get("page_size"):
                SearchValidator.validate_page_size(
                    request.query_params.get("page_size")
                )
            queryset = SearchService().execute(
                self.resource, query_params=request.query_params, user=request.user
            )
        except ValidationError as exc:
            return self.error_response("VALIDATION_ERROR", str(exc), status=400)
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        return PaginationService().paginate_response(
            request, queryset, self.serializer_class
        )


class JobSearchView(BaseSearchView):
    permission_classes = [permissions.AllowAny]
    resource = SearchResource.JOBS
    serializer_class = JobSearchResultSerializer


class VacancySearchView(BaseSearchView):
    permission_classes = [permissions.AllowAny]
    resource = SearchResource.FACULTY
    serializer_class = VacancySearchResultSerializer


class CompanySearchView(BaseSearchView):
    permission_classes = [permissions.AllowAny]
    resource = SearchResource.COMPANIES
    serializer_class = CompanySearchResultSerializer


class CollegeSearchView(BaseSearchView):
    permission_classes = [permissions.AllowAny]
    resource = SearchResource.COLLEGES
    serializer_class = CollegeSearchResultSerializer


class ApplicationSearchView(BaseSearchView):
    permission_classes = [permissions.IsAuthenticated]
    resource = SearchResource.APPLICATIONS
    serializer_class = ApplicationSearchResultSerializer


class InvoiceSearchView(BaseSearchView):
    permission_classes = [permissions.IsAuthenticated, IsEnterpriseAdmin]
    resource = SearchResource.INVOICES
    serializer_class = InvoiceSearchResultSerializer


class GuaranteeSearchView(BaseSearchView):
    permission_classes = [permissions.IsAuthenticated, IsEnterpriseAdmin]
    resource = SearchResource.GUARANTEES
    serializer_class = GuaranteeSearchResultSerializer


class JobSeekerSearchView(BaseSearchView):
    permission_classes = [permissions.IsAuthenticated]
    resource = SearchResource.JOB_SEEKERS
    serializer_class = JobSeekerSearchResultSerializer

    @extend_schema(responses={200: dict})
    def get(self, request):
        from django.core.exceptions import PermissionDenied, ValidationError

        from apps.search.validators.search_validators import SearchValidator

        try:
            if request.query_params.get("page_size"):
                SearchValidator.validate_page_size(
                    request.query_params.get("page_size")
                )
            queryset = SearchService().execute(
                self.resource, query_params=request.query_params, user=request.user
            )
        except ValidationError as exc:
            return self.error_response("VALIDATION_ERROR", str(exc), status=400)
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        return PaginationService().paginate_response(
            request,
            queryset,
            self.serializer_class,
            context={"viewer": request.user},
        )


class RecruiterSearchView(BaseSearchView):
    permission_classes = [permissions.IsAuthenticated, IsEnterpriseAdmin]
    resource = SearchResource.RECRUITERS
    serializer_class = RecruiterSearchResultSerializer


class ProfessorSearchView(BaseSearchView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrCollegeUser]
    resource = SearchResource.PROFESSORS
    serializer_class = ProfessorSearchResultSerializer


class AdminGlobalSearchView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEnterpriseAdmin]
    throttle_classes = [BruteForceIPThrottle, SearchEndpointThrottle]

    
    @extend_schema(responses={200: dict})
    def get(self, request):
        from django.core.exceptions import PermissionDenied, ValidationError

        try:
            data = SearchService().global_search(
                query_params=request.query_params, user=request.user
            )
        except ValidationError as exc:
            return self.error_response("VALIDATION_ERROR", str(exc), status=400)
        except PermissionDenied as exc:
            return self.error_response("FORBIDDEN", str(exc), status=403)
        return self.success_response(data)
