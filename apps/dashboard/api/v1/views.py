from drf_spectacular.utils import extend_schema

from rest_framework import permissions
from apps.authentication.permissions.throttles import DashboardAPIThrottle

from apps.core.permissions.base import (
    IsCollegeUser,
    IsITDomainUser,
    IsPlatformAdmin,
    IsProfessorUser,
)
from apps.core.views.base import EnvelopeAPIView
from apps.dashboard.services.dashboard_service import DashboardService


class SeekerDashboardView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [DashboardAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(DashboardService().seeker_dashboard(request.user))


class RecruiterDashboardView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsITDomainUser]
    throttle_classes = [DashboardAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(
            DashboardService().recruiter_dashboard(request.user)
        )


class ProfessorDashboardView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsProfessorUser]
    throttle_classes = [DashboardAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(
            DashboardService().professor_dashboard(request.user)
        )


class CollegeDashboardView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCollegeUser]
    throttle_classes = [DashboardAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(DashboardService().college_dashboard(request.user))


class AdminDashboardView(EnvelopeAPIView):
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]
    throttle_classes = [DashboardAPIThrottle]

    @extend_schema(responses={200: dict})
    def get(self, request):
        return self.success_response(DashboardService().admin_dashboard())
