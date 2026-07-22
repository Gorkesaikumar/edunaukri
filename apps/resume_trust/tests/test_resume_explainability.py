"""Unit tests for Explainable Resume Trust Analysis & Resume Match Score."""

from __future__ import annotations

import pytest
from django.core.cache import cache

from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.it_recruitment.models import JobSeekerProfile
from apps.academic_recruitment.models.professor import ProfessorProfile
from apps.it_recruitment.services.jobseeker_resume_portal_service import JobSeekerResumePortalService
from apps.academic_recruitment.services.professor_resume_portal_service import ProfessorResumePortalService
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService
from apps.resume_trust.services.resume_validators import extract_resume_diagnostics


@pytest.mark.django_db
class TestResumeExplainability:

    @pytest.fixture
    def it_user(self):
        return ITUser.objects.create_user(email="explain.it@edunaukri.com", password="Password123!")

    @pytest.fixture
    def it_profile(self, it_user):
        return JobSeekerProfile.objects.create(user=it_user, first_name="Explain", last_name="Seeker")

    @pytest.fixture
    def faculty_user(self):
        return ProfessorUser.objects.create_user(email="explain.prof@edunaukri.com", password="Password123!")

    @pytest.fixture
    def faculty_profile(self, faculty_user):
        return ProfessorProfile.objects.create(user=faculty_user, first_name="Dr. Explain", last_name="Professor")

    def test_extract_resume_diagnostics_valid_resume(self):
        raw_text = """
        Praveen Kumar
        Email: praveen@gmail.com
        Phone: 9876543210
        Professional Summary: Experienced Full Stack Developer.
        Skills: Python, Django, PostgreSQL
        Education: B.Tech Computer Science
        Experience: Senior Software Engineer at Tech Corp
        Projects: E-commerce Platform, Trust Engine
        Certifications: AWS Certified Developer
        LinkedIn: linkedin.com/in/praveen
        """
        parsed = {
            "name": "Praveen Kumar",
            "email": "praveen@gmail.com",
            "phone": "9876543210",
            "skills": ["Python", "Django", "PostgreSQL"],
            "education": ["B.Tech"],
            "experience": ["Senior Software Engineer"],
            "projects": ["E-commerce Platform"],
            "certifications": ["AWS Certified Developer"],
        }
        diag = extract_resume_diagnostics(raw_text, parsed)

        assert "Candidate Name" in diag["passed_checks"]
        assert "Email Address" in diag["passed_checks"]
        assert "Skills & Technical Stack" in diag["passed_checks"]
        assert "Projects & Portfolio" in diag["passed_checks"]
        assert "Skills" in diag["detected_sections"]
        assert len(diag["recommendations"]) > 0

    def test_extract_resume_diagnostics_missing_sections(self):
        raw_text = """
        Praveen Kumar
        Email: praveen@gmail.com
        Phone: 9876543210
        Skills: Python, Django
        Education: B.Tech
        """
        diag = extract_resume_diagnostics(raw_text, None)

        assert "Projects" in diag["missing_sections"]
        assert any("summary" in r.lower() for r in diag["recommendations"])

    def test_trust_analysis_service_returns_explainability(self, it_profile):
        cache.clear()
        service = ResumeFraudDetectionService()
        raw_text = """
        Nakul Deshmukh
        Email: nakul@gmail.com
        Phone: 9876543210
        Professional Summary: Software Engineer with 5 years experience.
        Skills: Python, Django, PostgreSQL
        Education: B.Tech Computer Science
        Experience: Developer at Tech Solutions
        """
        res = service.initiate_analysis(seeker_user_id=it_profile.user.pk, domain="it", raw_text=raw_text)

        assert res["status"] == "SUCCESS"
        portal_svc = JobSeekerResumePortalService()
        ctx = portal_svc.build(it_profile)

        assert "passed_checks" in ctx.trust_report
        assert len(ctx.trust_report["passed_checks"]) > 0
        assert "reason" in ctx.trust_report
        assert ctx.match_diagnostics["status"] in ["Good Match", "Excellent Match", "Needs Improvement"]
        assert len(ctx.match_diagnostics["detected_skills"]) > 0

    def test_failed_trust_analysis_returns_failure_explainability(self, it_profile):
        cache.clear()
        service = ResumeFraudDetectionService()
        invoice_text = """
        TAX INVOICE
        Invoice No: INV-100200
        Billed To: Corporate Client
        Subtotal: $500.00
        Balance Due: $500.00
        """
        res = service.initiate_analysis(seeker_user_id=it_profile.user.pk, domain="it", raw_text=invoice_text)

        assert res["status"] == "FAILED"
        portal_svc = JobSeekerResumePortalService()
        ctx = portal_svc.build(it_profile)

        assert ctx.match_score == 0
        assert ctx.match_diagnostics["status"] == "Not Available"
        assert len(ctx.match_diagnostics["possible_reasons"]) > 0
        assert "recommendation" in ctx.match_diagnostics
