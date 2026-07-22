"""Unit and integration tests for Resume Match Score dependency on Resume Trust Analysis."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from django.core.cache import cache

from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.it_recruitment.models import JobSeekerProfile
from apps.academic_recruitment.models.professor import ProfessorProfile
from apps.it_recruitment.services.jobseeker_resume_portal_service import JobSeekerResumePortalService
from apps.academic_recruitment.services.professor_resume_portal_service import ProfessorResumePortalService
from apps.resume_trust.models import AnalysisStatus, ResumeFraudAnalysis
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService


@pytest.mark.django_db
class TestResumeMatchScoreDependency:

    @pytest.fixture
    def it_user(self):
        return ITUser.objects.create_user(email="match.it@edunaukri.com", password="Password123!")

    @pytest.fixture
    def it_profile(self, it_user):
        return JobSeekerProfile.objects.create(user=it_user, first_name="Match", last_name="ITSeeker")

    @pytest.fixture
    def faculty_user(self):
        return ProfessorUser.objects.create_user(email="match.faculty@edunaukri.com", password="Password123!")

    @pytest.fixture
    def faculty_profile(self, faculty_user):
        return ProfessorProfile.objects.create(user=faculty_user, first_name="Dr. Match", last_name="Professor")

    def test_failed_trust_analysis_resets_it_match_score_to_zero(self, it_profile):
        cache.clear()
        service = ResumeFraudDetectionService()

        # Ingest an invoice PDF to trigger validation failure
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-881100
        Billed To: ACME Inc
        Subtotal: $450.00
        Balance Due: $450.00
        GSTIN: 27AAAAA0000A1Z5
        """
        service.initiate_analysis(seeker_user_id=it_profile.user.pk, domain="it", raw_text=invoice_text)

        portal_svc = JobSeekerResumePortalService()
        ctx = portal_svc.build(it_profile)

        assert ctx.match_score == 0
        assert "cannot be calculated" in ctx.match_explanation.lower()
        match_card = next(c for c in ctx.summary if c.key == "match")
        assert match_card.value == "N/A"

    def test_valid_resume_generates_normal_it_match_score(self, it_profile):
        cache.clear()
        service = ResumeFraudDetectionService()
        valid_text = """
        Nakul Deshmukh
        Email: nakul@gmail.com
        Phone: 9876543210
        Skills: Python, Django, PostgreSQL, JavaScript
        Education: B.Tech Computer Science
        Experience: Senior Software Engineer at Tech Corp (2020-2026)
        """
        service.initiate_analysis(seeker_user_id=it_profile.user.pk, domain="it", raw_text=valid_text)

        portal_svc = JobSeekerResumePortalService()
        ctx = portal_svc.build(it_profile)

        assert ctx.trust_report["status"] == AnalysisStatus.SUCCESS
        assert ctx.match_score >= 0
        match_card = next(c for c in ctx.summary if c.key == "match")
        assert match_card.value.endswith("%")

    def test_failed_trust_analysis_resets_faculty_match_score_to_zero(self, faculty_profile):
        cache.clear()
        service = ResumeFraudDetectionService()
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-990011
        Billed To: University Inc
        Subtotal: $1,000.00
        Balance Due: $1,000.00
        """
        service.initiate_analysis(seeker_user_id=faculty_profile.user.pk, domain="faculty", raw_text=invoice_text)

        portal_svc = ProfessorResumePortalService()
        ctx = portal_svc.build(faculty_profile)

        assert ctx.match_score == 0
        assert "cannot be calculated" in ctx.match_explanation.lower()
        match_card = next(c for c in ctx.summary if c.key == "match")
        assert match_card.value == "N/A"
