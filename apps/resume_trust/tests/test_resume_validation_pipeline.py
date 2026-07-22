"""Unit and integration tests for mandatory Resume Trust Validation Pipeline and non-resume detection."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from django.core.cache import cache

from apps.accounts.models.it_user import ITUser
from apps.it_recruitment.models import JobSeekerProfile
from apps.resume_trust.models import AnalysisStatus, ResumeFraudAnalysis
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService
from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
from apps.resume_trust.services.resume_validators import (
    ResumeCompletenessValidator,
    ResumeDetectionService,
    ResumeReadabilityValidator,
)


@pytest.mark.django_db
class TestResumeValidationPipeline:

    @pytest.fixture
    def user(self):
        return ITUser.objects.create_user(email="validation.test@edunaukri.com", password="Password123!")

    @pytest.fixture
    def profile(self, user):
        return JobSeekerProfile.objects.create(user=user, first_name="Validation", last_name="Tester")

    def test_unreadable_short_text_fails_readability(self):
        validator = ResumeReadabilityValidator()
        res = validator.validate_stored_file(None, raw_text="Short text")
        assert res.is_valid is False
        assert res.error_code == "UNREADABLE_OR_EMPTY"

    def test_invoice_pdf_fails_resume_detection(self):
        detector = ResumeDetectionService()
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-2026-001
        Date: 23/07/2026
        Billed To: ACME Corporation
        Item Description: Cloud Hosting Services
        Subtotal: $500.00
        Tax (18%): $90.00
        Total Amount: $590.00
        Balance Due: $590.00
        Payment Terms: Net 30
        GSTIN: 27AAAAA0000A1Z5
        """
        res = detector.detect_resume(raw_text=invoice_text)
        assert res.is_valid is False
        assert res.error_code == "NOT_A_RESUME"
        assert "invoice" in res.error_message.lower()

    def test_incomplete_text_fails_completeness(self):
        validator = ResumeCompletenessValidator()
        incomplete_text = "Random brochure copy about company mission and goals."
        res = validator.validate_completeness(raw_text=incomplete_text)
        assert res.is_valid is False
        assert res.error_code == "INCOMPLETE_RESUME"

    def test_valid_resume_passes_all_validators(self):
        valid_text = """
        Nakul Deshmukh
        Email: nakul.deshmukh@gmail.com
        Phone: +91 9876543210
        LinkedIn: linkedin.com/in/nakul-deshmukh
        
        Professional Summary:
        Senior Python Django Developer with 5+ years of experience building web applications.
        
        Skills:
        Python, Django, REST APIs, PostgreSQL, Redis, Celery, Docker, JavaScript.
        
        Education:
        B.Tech in Computer Science & Engineering - Pune University (2017 - 2021)
        
        Work Experience:
        Software Engineer - Tech Solutions Pvt Ltd (2021 - Present)
        - Developed backend RESTful APIs using Django REST Framework.
        """
        r_res = ResumeReadabilityValidator().validate_stored_file(None, raw_text=valid_text)
        d_res = ResumeDetectionService().detect_resume(raw_text=valid_text)
        c_res = ResumeCompletenessValidator().validate_completeness(raw_text=valid_text)

        assert r_res.is_valid is True
        assert d_res.is_valid is True
        assert c_res.is_valid is True

    def test_initiate_analysis_on_invoice_pdf_halts_and_returns_failed(self, user):
        cache.clear()
        service = ResumeFraudDetectionService()
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-998822
        Billed To: Client Inc
        Subtotal: $1,200.00
        Balance Due: $1,200.00
        GSTIN: 27AAAAA0000A1Z5
        """
        res = service.initiate_analysis(
            seeker_user_id=user.pk,
            domain="it",
            raw_text=invoice_text,
        )

        assert res["status"] == "FAILED"
        assert res["has_analysis"] is False
        assert res["trust_score"] is None
        assert res["risk_level"] == "NOT_EVALUATED"
        assert res["show_unverified_popup"] is True

        analysis_db = ResumeFraudAnalysis.objects.get(id=res["id"])
        assert analysis_db.status == AnalysisStatus.FAILED
        assert "invoice" in analysis_db.error_message.lower()

    def test_report_service_returns_failed_status_when_validation_fails(self, user):
        cache.clear()
        service = ResumeFraudDetectionService()
        report_service = ResumeFraudReportService()

        invoice_text = """
        TAX INVOICE
        Invoice No: INV-1002
        Billed To: Acme Corp
        Subtotal: $300.00
        Balance Due: $300.00
        GSTIN: 27AAAAA0000A1Z5
        """
        service.initiate_analysis(seeker_user_id=user.pk, domain="it", raw_text=invoice_text)

        report = report_service.get_user_latest_report(user.pk, domain="it")
        assert report["has_analysis"] is False
        assert report["status"] == "FAILED"
        assert report["trust_score"] is None
        assert report["risk_level"] == "NOT_EVALUATED"
        assert report["show_unverified_popup"] is True
