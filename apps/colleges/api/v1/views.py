from drf_spectacular.utils import extend_schema

from rest_framework import permissions, status
from apps.authentication.permissions.throttles import ApplicationThrottle

from apps.colleges.api.schema import (
    institution_activate_schema,
    institution_branding_schema,
    institution_campus_create_schema,
    institution_campus_detail_schema,
    institution_campus_list_schema,
    institution_create_schema,
    institution_dashboard_schema,
    institution_deactivate_schema,
    institution_delete_schema,
    institution_department_add_schema,
    institution_department_list_schema,
    institution_department_remove_schema,
    institution_detail_schema,
    institution_document_list_schema,
    institution_document_remove_schema,
    institution_document_upload_schema,
    institution_list_schema,
    institution_member_add_schema,
    institution_member_list_schema,
    institution_member_remove_schema,
    institution_update_schema,
)
from apps.colleges.api.v1.serializers import (
    DepartmentAddSerializer,
    InstitutionBrandingSerializer,
    InstitutionCampusSerializer,
    InstitutionCampusWriteSerializer,
    InstitutionCreateSerializer,
    InstitutionDocumentSerializer,
    InstitutionDocumentUploadSerializer,
    InstitutionMemberAddSerializer,
    InstitutionMemberSerializer,
    InstitutionSerializer,
    InstitutionUpdateSerializer,
)
from apps.colleges.permissions.institution_permissions import (
    IsInstitutionAdmin,
    IsInstitutionMember,
)
from apps.colleges.selectors.college_selector import (
    CollegeDepartmentSelector,
    CollegeMemberSelector,
    CollegeSelector,
    InstitutionCampusSelector,
    InstitutionDocumentSelector,
)
from apps.colleges.services.department_management_service import (
    DepartmentManagementService,
)
from apps.colleges.services.institution_branding_service import (
    InstitutionBrandingService,
)
from apps.colleges.services.institution_campus_service import InstitutionCampusService
from apps.colleges.services.institution_document_service import (
    InstitutionDocumentService,
)
from apps.colleges.services.institution_member_service import InstitutionMemberService
from apps.colleges.services.institution_service import InstitutionService
from apps.colleges.services.institution_statistics_service import (
    InstitutionStatisticsService,
)
from apps.core.pagination import paginate_envelope
from apps.core.permissions.base import IsCollegeUser
from apps.core.views.base import EnvelopeAPIView


class _CollegeView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [ApplicationThrottle]

    def _institution_or_error(self, college_id):
        institution = CollegeSelector().get_or_none(college_id)
        if not institution:
            return None, self.error_response(
                "NOT_FOUND", "Institution not found.", status=404
            )
        return institution, None


class InstitutionListCreateView(_CollegeView):
    @institution_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        institutions = CollegeSelector().for_college_user(request.user)
        return paginate_envelope(request, institutions, InstitutionSerializer)

    @institution_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request):
        serializer = InstitutionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        institution = InstitutionService().create_institution(
            college_user=request.user, data=serializer.validated_data
        )
        return self.success_response(
            InstitutionSerializer(institution).data, status=status.HTTP_201_CREATED
        )


class InstitutionDetailView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionMember,
    ]

    @institution_detail_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        return self.success_response(InstitutionSerializer(institution).data)

    @institution_update_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = InstitutionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        institution = InstitutionService().update_institution(
            institution=institution,
            college_user=request.user,
            data=serializer.validated_data,
        )
        return self.success_response(InstitutionSerializer(institution).data)

    @institution_delete_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        InstitutionService().soft_delete(
            institution=institution, college_user=request.user
        )
        return self.success_response({"deleted": True})


class InstitutionActivateView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_activate_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        institution = InstitutionService().activate(
            institution=institution, college_user=request.user
        )
        return self.success_response(InstitutionSerializer(institution).data)


class InstitutionDeactivateView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_deactivate_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        institution = InstitutionService().deactivate(
            institution=institution, college_user=request.user
        )
        return self.success_response(InstitutionSerializer(institution).data)


class InstitutionBrandingView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_branding_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = InstitutionBrandingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = InstitutionBrandingService()
        if serializer.validated_data.get("logo_file_id"):
            institution = service.set_logo(
                institution=institution,
                college_user=request.user,
                user=request.user,
                logo_file_id=serializer.validated_data["logo_file_id"],
            )
        if serializer.validated_data.get("banner_file_id"):
            institution = service.set_banner(
                institution=institution,
                college_user=request.user,
                user=request.user,
                banner_file_id=serializer.validated_data["banner_file_id"],
            )
        return self.success_response(InstitutionSerializer(institution).data)


class InstitutionDashboardView(_CollegeView):
    @institution_dashboard_schema
    @extend_schema(responses={200: dict})
    def get(self, request):
        summary = InstitutionStatisticsService().college_dashboard(request.user)
        return self.success_response(summary)


class InstitutionDepartmentListView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionMember,
    ]

    @institution_department_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        links = CollegeDepartmentSelector().for_college(college_id)
        data = [
            {
                "id": str(link.pk),
                "department_id": str(link.department_id),
                "name": link.department.name,
                "category": link.department.category,
            }
            for link in links.select_related("department")
        ]
        return self.success_response(data)

    @institution_department_add_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = DepartmentAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = DepartmentManagementService().add_department(
            institution=institution,
            college_user=request.user,
            name=serializer.validated_data["name"],
            category=serializer.validated_data.get("category", ""),
        )
        return self.success_response(
            {
                "id": str(link.pk),
                "department_id": str(link.department_id),
                "name": link.department.name,
            },
            status=status.HTTP_201_CREATED,
        )


class InstitutionDepartmentDetailView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_department_remove_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, college_id, link_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        DepartmentManagementService().remove_department(
            institution=institution, college_user=request.user, link_id=link_id
        )
        return self.success_response({"removed": True})


class InstitutionCampusListCreateView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionMember,
    ]

    @institution_campus_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        campuses = InstitutionCampusSelector().for_college(college_id)
        return self.success_response(
            InstitutionCampusSerializer(campuses, many=True).data
        )

    @institution_campus_create_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = InstitutionCampusWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        campus = InstitutionCampusService().add_campus(
            institution=institution,
            college_user=request.user,
            data=serializer.validated_data,
        )
        return self.success_response(
            InstitutionCampusSerializer(campus).data, status=status.HTTP_201_CREATED
        )


class InstitutionCampusDetailView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_campus_detail_schema
    @extend_schema(request=None, responses={200: dict})
    def patch(self, request, college_id, campus_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = InstitutionCampusWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        campus = InstitutionCampusService().update_campus(
            institution=institution,
            college_user=request.user,
            campus_id=campus_id,
            data=serializer.validated_data,
        )
        return self.success_response(InstitutionCampusSerializer(campus).data)

    @institution_campus_detail_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, college_id, campus_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        InstitutionCampusService().delete_campus(
            institution=institution, college_user=request.user, campus_id=campus_id
        )
        return self.success_response({"deleted": True})


class InstitutionMemberListView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionMember,
    ]

    @institution_member_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        members = CollegeMemberSelector().for_college(college_id)
        return self.success_response(
            InstitutionMemberSerializer(members, many=True).data
        )

    @institution_member_add_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = InstitutionMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member = InstitutionMemberService().add_member(
            institution=institution,
            actor=request.user,
            user_email=serializer.validated_data["user_email"],
            role=serializer.validated_data["role"],
        )
        return self.success_response(
            InstitutionMemberSerializer(member).data, status=status.HTTP_201_CREATED
        )


class InstitutionMemberDetailView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_member_remove_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, college_id, member_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        InstitutionMemberService().remove_member(
            institution=institution, actor=request.user, member_id=member_id
        )
        return self.success_response({"removed": True})


class InstitutionDocumentListView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionMember,
    ]

    @institution_document_list_schema
    @extend_schema(responses={200: dict})
    def get(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        documents = InstitutionDocumentSelector().for_college(
            college_id, document_type=request.query_params.get("document_type")
        )
        return self.success_response(
            InstitutionDocumentSerializer(documents, many=True).data
        )

    @institution_document_upload_schema
    @extend_schema(request=None, responses={200: dict})
    def post(self, request, college_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        serializer = InstitutionDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = InstitutionDocumentService().attach_document(
            institution=institution,
            college_user=request.user,
            user=request.user,
            document_type=serializer.validated_data["document_type"],
            stored_file_id=serializer.validated_data["stored_file_id"],
            title=serializer.validated_data.get("title", ""),
        )
        return self.success_response(
            InstitutionDocumentSerializer(document).data, status=status.HTTP_201_CREATED
        )


class InstitutionDocumentDetailView(_CollegeView):
    permission_classes = [
        permissions.IsAuthenticated,
        IsCollegeUser,
        IsInstitutionAdmin,
    ]

    @institution_document_remove_schema
    @extend_schema(request=None, responses={200: dict})
    def delete(self, request, college_id, document_id):
        institution, error = self._institution_or_error(college_id)
        if error:
            return error
        InstitutionDocumentService().remove_document(
            institution=institution, college_user=request.user, document_id=document_id
        )
        return self.success_response({"removed": True})
