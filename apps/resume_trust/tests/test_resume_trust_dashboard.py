"""Unit tests verifying Resume Trust Analysis integration into IT and Faculty Resume Dashboards."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.documents.models import StoredFile
from apps.it_recruitment.models import JobSeekerProfile
from apps.academic_recruitment.models import ProfessorProfile
from apps.it_recruitment.services.jobseeker_resume_portal_service import JobSeekerResumePortalService
from apps.academic_recruitment.services.professor_resume_portal_service import ProfessorResumePortalService
from apps.resume_trust.models import FraudDomainType


@pytest.mark.django_db
class TestResumeTrustDashboardIntegration:

    @pytest.fixture
    def it_profile(self):
        user = ITUser.objects.create_user(email="it.dashboard.test@edunaukri.com", password="Password123!")
        profile = JobSeekerProfile.objects.create(user=user, first_name="IT", last_name="Candidate")
        return profile

    @pytest.fixture
    def faculty_profile(self):
        user = ProfessorUser.objects.create_user(email="prof.dashboard.test@edunaukri.com", password="Password123!")
        profile = ProfessorProfile.objects.create(user=user, first_name="Faculty", last_name="Candidate")
        return profile

    def test_it_resume_portal_context_includes_trust_report(self, it_profile):
        service = JobSeekerResumePortalService()
        context = service.build(it_profile)

        assert hasattr(context, "trust_report")
        assert isinstance(context.trust_report, dict)
        assert "has_analysis" in context.trust_report
        assert context.trust_report["has_analysis"] is False

    def test_faculty_resume_portal_context_includes_trust_report(self, faculty_profile):
        service = ProfessorResumePortalService()
        context = service.build(faculty_profile)

        assert hasattr(context, "trust_report")
        assert isinstance(context.trust_report, dict)
        assert "has_analysis" in context.trust_report
        assert context.trust_report["has_analysis"] is False

    @patch("apps.resume_trust.services.resume_fraud_report_service.ResumeFraudReportService.get_user_latest_report")
    def test_it_resume_portal_reflects_active_trust_report(self, mock_report, it_profile):
        mock_report.return_value = {
            "has_analysis": True,
            "trust_score": 85,
            "risk_score": 15,
            "risk_level": "LOW",
            "warning_count": 1,
            "resume_version": 2,
            "analysis_duration_ms": 45,
            "status": "SUCCESS",
            "created_at": "2026-07-22T23:30:00Z",
            "recommendation_message": "Resume verified.",
        }

        service = JobSeekerResumePortalService()
        context = service.build(it_profile)

        assert context.trust_report["has_analysis"] is True
        assert context.trust_report["trust_score"] == 85
        assert context.trust_report["risk_level"] == "LOW"
        assert context.trust_report["resume_version"] == 2

    def test_report_service_popup_warning_flags(self, it_profile):
        from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
        from django.core.cache import cache
        service = ResumeFraudReportService()

        # Mock repository to return analysis with trust_score = 50 (< threshold 70)
        mock_analysis = MagicMock()
        mock_analysis.trust_score = 50
        mock_analysis.risk_score = 50
        mock_analysis.risk_level = "HIGH"
        mock_analysis.warning_count = 2
        mock_analysis.status = "SUCCESS"

        cache.clear()
        with patch.object(service.repository, "get_latest_for_user", return_value=mock_analysis):
            with patch.object(service.mapper, "to_dict", return_value={"trust_score": 50, "risk_level": "HIGH"}):
                report = service.get_user_latest_report(it_profile.user.pk, domain="it")
                assert report["has_analysis"] is True
                assert report["popup_trust_threshold"] == 70
                assert report["show_warning_popup"] is True

        # Mock repository to return analysis with trust_score = 90 (>= threshold 70)
        cache.clear()
        with patch.object(service.repository, "get_latest_for_user", return_value=mock_analysis):
            with patch.object(service.mapper, "to_dict", return_value={"trust_score": 90, "risk_level": "LOW"}):
                report = service.get_user_latest_report(it_profile.user.pk, domain="it")
                assert report["popup_trust_threshold"] == 70
                assert report["show_warning_popup"] is False

    def test_get_recruiter_trust_report_sanitizes_internal_details(self, it_profile):
        from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
        service = ResumeFraudReportService()

        mock_analysis = MagicMock()
        mock_analysis.id = "11111111-1111-1111-1111-111111111111"
        mock_analysis.trust_score = 75
        mock_analysis.risk_score = 25
        mock_analysis.risk_level = "MEDIUM"
        mock_analysis.recommendation = "FLAG_FOR_REVIEW"
        mock_analysis.resume_version = 1
        mock_analysis.warning_count = 1
        mock_analysis.status = "SUCCESS"
        mock_analysis.created_at = None
        mock_analysis.analysis_report = {
            "recommendation_message": "Review candidate credentials.",
            "warnings": [
                {
                    "rule_code": "SKILL_001",
                    "category": "Skills",
                    "severity": "MEDIUM",
                    "title": "Skill Keyword Stuffing",
                    "description": "Found 45 repeated tech stack keywords.",
                    "recommendation": "Conduct technical screening.",
                    "raw_penalty": 20,
                    "weighted_penalty": 20,
                    "evidence_snippet": {"internal_dict": True},
                }
            ],
        }

        with patch.object(service.repository, "get_latest_for_user", return_value=mock_analysis):
            report = service.get_recruiter_trust_report(it_profile.user.pk, domain="it")
            assert report["has_analysis"] is True
            assert report["trust_score"] == 75
            assert report["risk_level"] == "MEDIUM"
            assert report["recommendation"] == "FLAG_FOR_REVIEW"
            assert report["warning_count"] == 1
            assert len(report["warnings"]) == 1

            warning = report["warnings"][0]
            assert warning["category"] == "Skills"
            assert warning["title"] == "Skill Keyword Stuffing"
            assert warning["severity"] == "MEDIUM"
            assert warning["description"] == "Found 45 repeated tech stack keywords."
            assert warning["recommendation"] == "Conduct technical screening."
            # Internal engine details must be stripped out
            assert "rule_code" not in warning
            assert "raw_penalty" not in warning
            assert "weighted_penalty" not in warning
            assert "evidence_snippet" not in warning
