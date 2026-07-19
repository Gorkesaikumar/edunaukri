"""Tests for DashboardRedirectService — all 5 user roles and error paths."""

from __future__ import annotations

import pytest

from apps.social_auth.services.dashboard_redirect_service import (
    DashboardRedirectResult,
    DashboardRedirectService,
)

pytestmark = pytest.mark.django_db

svc = DashboardRedirectService()


class TestAdminUser:
    def test_administrator_role(self, db):
        from apps.accounts.models.admin_user import AdminUser

        user = AdminUser.objects.create(email="admin@edunaukri.com")
        result = svc.resolve(user)
        assert isinstance(result, DashboardRedirectResult)
        assert result.role == "Administrator"
        assert result.role_key == "administrator"
        assert "dashboard" in result.dashboard_url


class TestProfessorUser:
    def test_faculty_job_seeker_role(self, db):
        from apps.accounts.models.professor_user import ProfessorUser

        user = ProfessorUser.objects.create(
            email="prof@university.edu",
        )
        result = svc.resolve(user)
        assert result.role == "Faculty Job Seeker"
        assert result.role_key == "faculty_job_seeker"
        assert "dashboard" in result.dashboard_url


class TestCollegeUser:
    def test_faculty_recruiter_role(self, db):
        from apps.accounts.models.college_user import CollegeUser

        user = CollegeUser.objects.create(
            email="college@university.edu",
        )
        result = svc.resolve(user)
        assert result.role == "Faculty Recruiter"
        assert result.role_key == "faculty_recruiter"
        assert "dashboard" in result.dashboard_url


class TestITUser:
    def test_job_seeker_role(self, db):
        from apps.accounts.constants.enums import ITUserRoleType
        from apps.accounts.models.it_user import ITUser
        from apps.accounts.services.role_assignment_service import (
            RoleAssignmentService,
        )

        user = ITUser.objects.create(email="seeker@example.com")
        RoleAssignmentService().assign_it_role(
            user=user, role=ITUserRoleType.JOB_SEEKER
        )
        result = svc.resolve(user)
        assert result.role == "Job Seeker"
        assert result.role_key == "job_seeker"
        assert "dashboard" in result.dashboard_url

    def test_recruiter_role(self, db):
        from apps.accounts.constants.enums import ITUserRoleType
        from apps.accounts.models.it_user import ITUser
        from apps.accounts.services.role_assignment_service import (
            RoleAssignmentService,
        )

        user = ITUser.objects.create(email="recruiter@company.com")
        RoleAssignmentService().assign_it_role(
            user=user, role=ITUserRoleType.RECRUITER
        )
        result = svc.resolve(user)
        assert result.role == "Recruiter"
        assert result.role_key == "recruiter"
        assert "dashboard" in result.dashboard_url

    def test_it_user_without_role_raises(self, db):
        from apps.accounts.models.it_user import ITUser

        user = ITUser.objects.create(email="norole@example.com")
        with pytest.raises(ValueError, match="neither a Job Seeker"):
            svc.resolve(user)


class TestUnrecognizedUserType:
    def test_unknown_user_type_raises(self, db):
        """A user model not in the recognised list should raise ValueError."""

        class UnknownUser:
            pk = "some-uuid"
            email = "unknown@example.com"

        with pytest.raises(ValueError, match="unrecognised user type"):
            svc.resolve(UnknownUser())
