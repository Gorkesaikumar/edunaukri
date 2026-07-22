"""Comprehensive production hardening unit, integration, and regression tests for Resume Trust Engine."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from celery.exceptions import SoftTimeLimitExceeded

from apps.accounts.models.it_user import ITUser
from apps.it_recruitment.models import JobSeekerProfile
from apps.resume_trust.models import FraudDomainType, AnalysisStatus, ResumeFraudAnalysis
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService
from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
from apps.resume_trust.tasks import run_resume_trust_analysis_task


@pytest.mark.django_db
class TestResumeTrustProductionHardening:

    @pytest.fixture
    def user(self):
        return ITUser.objects.create_user(email="hardening.test@edunaukri.com", password="Password123!")

    @pytest.fixture
    def profile(self, user):
        return JobSeekerProfile.objects.create(user=user, first_name="Hardening", last_name="User")

    def test_caching_and_invalidation(self, user):
        report_service = ResumeFraudReportService()
        cache_key = f"trust_candidate_report_it_{user.pk}"
        cache.delete(cache_key)

        # First call fetches from DB and populates cache
        report1 = report_service.get_user_latest_report(user.pk, domain="it")
        assert report1["has_analysis"] is False
        assert cache.get(cache_key) is not None

        # Verify second call retrieves from cache
        report2 = report_service.get_user_latest_report(user.pk, domain="it")
        assert report2 == report1

        # Clear cache and verify deletion
        report_service.clear_report_cache(user.pk, domain="it")
        assert cache.get(cache_key) is None

    def test_large_pdf_raw_text_truncation(self, user):
        service = ResumeFraudDetectionService()
        massive_text = "Nakul Deshmukh Email: nakul@gmail.com Phone: 9876543210 Education: BTech Skills: Python Django Experience: Developer\n" + ("A" * 300000)

        res = service.initiate_analysis(
            seeker_user_id=user.pk,
            domain="it",
            raw_text=massive_text,
        )
        assert res["status"] == AnalysisStatus.SUCCESS
        analysis = ResumeFraudAnalysis.objects.get(id=res["id"])
        assert analysis.status == AnalysisStatus.SUCCESS

    def test_error_handling_and_failed_status_recording(self, user):
        service = ResumeFraudDetectionService()
        valid_text = "Nakul Deshmukh Email: nakul@gmail.com Phone: 9876543210 Education: BTech Skills: Python Django Experience: Developer at ACME"

        # Force exception inside rule_engine.evaluate to test rollback & failure recording
        with patch.object(service.rule_engine, "evaluate", side_effect=ValueError("Test Engine Failure")):
            with pytest.raises(ValueError, match="Test Engine Failure"):
                service.initiate_analysis(seeker_user_id=user.pk, domain="it", raw_text=valid_text)

        failed_record = ResumeFraudAnalysis.objects.filter(seeker_user_id=user.pk, status=AnalysisStatus.FAILED).first()
        assert failed_record is not None
        assert "Test Engine Failure" in failed_record.error_message

    def test_celery_task_execution(self, user):
        task_res = run_resume_trust_analysis_task(
            seeker_user_id=user.pk,
            domain="it",
            raw_text="Nakul Deshmukh Email: nakul@gmail.com Phone: 9876543210 Skills: Python Django Education: BTech Experience: Developer 5 years.",
        )
        assert task_res["success"] is True
        assert "data" in task_res
        assert task_res["data"]["status"] == AnalysisStatus.SUCCESS

    def test_celery_task_soft_time_limit_exceeded(self, user):
        with patch("apps.resume_trust.tasks.ResumeFraudDetectionService.initiate_analysis", side_effect=SoftTimeLimitExceeded):
            task_res = run_resume_trust_analysis_task(seeker_user_id=user.pk, domain="it")
            assert task_res["success"] is False
            assert "timed out" in task_res["error"]

    def test_recruiter_report_endpoint_unauthorized(self, client):
        response = client.get("/api/resume-trust/recruiter-report/?seeker_user_id=999&domain=it")
        assert response.status_code == 401
