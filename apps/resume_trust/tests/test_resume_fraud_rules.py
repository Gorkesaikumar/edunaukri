"""Unit tests for the Resume Fraud Detection Rule Engine and all 8 rules."""

from __future__ import annotations

import pytest
from unittest.mock import patch

from apps.resume_trust.services.resume_fraud_rule_engine import ResumeFraudRuleEngine
from apps.resume_trust.services.rules.base_rule import RuleResult
from apps.resume_trust.services.rules.certification_validation_rule import CertificationValidationRule
from apps.resume_trust.services.rules.company_validation_rule import CompanyValidationRule
from apps.resume_trust.services.rules.contact_validation_rule import ContactValidationRule
from apps.resume_trust.services.rules.duplicate_keyword_rule import DuplicateKeywordRule
from apps.resume_trust.services.rules.education_validation_rule import EducationValidationRule
from apps.resume_trust.services.rules.resume_completeness_rule import ResumeCompletenessRule
from apps.resume_trust.services.rules.rule_registry import RULE_REGISTRY
from apps.resume_trust.services.rules.skill_inflation_rule import SkillInflationRule
from apps.resume_trust.services.rules.timeline_validation_rule import TimelineValidationRule


# ─────────────────────────────────────────────────────────────
# Rule Registry
# ─────────────────────────────────────────────────────────────

class TestRuleRegistry:
    def test_registry_has_all_eight_rules(self):
        codes = {r.RULE_CODE for r in RULE_REGISTRY}
        expected = {
            "TIMELINE_001", "EDUCATION_001", "SKILL_001", "KEYWORD_001",
            "CONTACT_001", "COMPLETENESS_001", "COMPANY_001", "CERT_001",
        }
        assert expected == codes

    def test_engine_auto_discovers_registry(self):
        engine = ResumeFraudRuleEngine()
        assert len(engine.registered_rule_codes) == 8


# ─────────────────────────────────────────────────────────────
# BaseRule contract
# ─────────────────────────────────────────────────────────────

class TestBaseRuleContract:
    def test_passing_result_produces_no_warning(self):
        rule = ContactValidationRule()
        result = RuleResult(
            rule_code="X", rule_name="X", passed=True,
            score_penalty=0, confidence=1.0, severity="LOW",
        )
        assert result.to_warning_dict() is None

    def test_failing_result_produces_warning_dict(self):
        rule = ContactValidationRule()
        result = RuleResult(
            rule_code="TEST_001", rule_name="Test Rule", passed=False,
            score_penalty=20, confidence=0.9, severity="HIGH",
            title="Test", description="desc",
        )
        w = result.to_warning_dict()
        assert w is not None
        assert w["rule_code"] == "TEST_001"
        assert w["severity"] == "HIGH"
        assert w["weight"] == 20


# ─────────────────────────────────────────────────────────────
# Timeline Validation Rule
# ─────────────────────────────────────────────────────────────

class TestTimelineValidationRule:
    def setup_method(self):
        self.rule = TimelineValidationRule()

    def test_valid_timeline_passes(self):
        data = {
            "experience": [
                {"company": "TechCorp", "start_date": "2018", "end_date": "2021"},
                {"company": "StartupX", "start_date": "2021", "end_date": "Present"},
            ]
        }
        result = self.rule.evaluate(data, "")
        assert result.passed

    def test_reversed_dates_fails(self):
        data = {
            "experience": [
                {"company": "BadCorp", "start_date": "2022", "end_date": "2019"},
            ]
        }
        result = self.rule.evaluate(data, "")
        assert not result.passed
        assert result.severity in ("MEDIUM", "HIGH")

    def test_no_data_passes_with_low_confidence(self):
        result = self.rule.evaluate({}, "")
        assert result.passed
        assert result.confidence <= 0.5


# ─────────────────────────────────────────────────────────────
# Education Validation Rule
# ─────────────────────────────────────────────────────────────

class TestEducationValidationRule:
    def setup_method(self):
        self.rule = EducationValidationRule()

    def test_clean_education_passes(self):
        data = {"education": [{"degree": "Bachelor of Engineering", "institution": "IIT Bombay"}]}
        result = self.rule.evaluate(data, "Bachelor of Engineering from IIT Bombay 2016")
        assert result.passed

    def test_diploma_mill_keyword_fails(self):
        result = self.rule.evaluate(
            {"education": [{"degree": "PhD"}]},
            "PhD from belford university in 2020",
        )
        assert not result.passed
        assert result.severity in ("MEDIUM", "HIGH")

    def test_multiple_phds_fails(self):
        data = {
            "education": [
                {"degree": "PhD in CS"},
                {"degree": "Ph.D in AI"},
            ]
        }
        result = self.rule.evaluate(data, "PhD in CS and Ph.D in AI")
        assert not result.passed


# ─────────────────────────────────────────────────────────────
# Skill Inflation Rule
# ─────────────────────────────────────────────────────────────

class TestSkillInflationRule:
    def setup_method(self):
        self.rule = SkillInflationRule()

    def test_reasonable_skills_passes(self):
        data = {"skills": ["Python", "Django", "PostgreSQL", "Docker", "Git"]}
        result = self.rule.evaluate(data, "")
        assert result.passed

    def test_excessive_skill_count_fails(self):
        skills = [f"Skill{i}" for i in range(65)]
        result = self.rule.evaluate({"skills": skills}, "")
        assert not result.passed
        assert result.score_penalty > 0

    def test_no_skills_passes_with_low_confidence(self):
        result = self.rule.evaluate({}, "")
        assert result.passed
        assert result.confidence < 0.5


# ─────────────────────────────────────────────────────────────
# Duplicate Keyword Rule
# ─────────────────────────────────────────────────────────────

class TestDuplicateKeywordRule:
    def setup_method(self):
        self.rule = DuplicateKeywordRule()

    def test_normal_text_passes(self):
        # Use a diverse resume text — not repetitive — to stay above unique_ratio threshold
        text = (
            "Developed scalable microservices using Python and Django REST framework for financial clients. "
            "Led cross-functional teams across product management, engineering, quality assurance, and design. "
            "Implemented CI/CD pipelines with Jenkins GitHub Actions Docker Kubernetes and Terraform. "
            "Collaborated with business stakeholders product owners and architects to deliver enterprise software. "
            "Mentored junior engineers conducted code reviews and established best practices for backend development. "
            "Designed relational schemas in PostgreSQL optimised slow queries and introduced Redis caching layer. "
            "Integrated third-party APIs including Stripe Razorpay Twilio SendGrid and OAuth providers. "
            "Contributed to open-source libraries and presented technical talks at internal knowledge-sharing sessions."
        )
        result = self.rule.evaluate({}, text)
        assert result.passed

    def test_keyword_stuffed_text_fails(self):
        # Single word repeated far beyond threshold
        stuffed = ("python " * 20 + "django " * 20 + "aws " * 20) * 3
        result = self.rule.evaluate({}, stuffed)
        assert not result.passed

    def test_short_text_passes(self):
        result = self.rule.evaluate({}, "Short resume text.")
        assert result.passed


# ─────────────────────────────────────────────────────────────
# Contact Validation Rule
# ─────────────────────────────────────────────────────────────

class TestContactValidationRule:
    def setup_method(self):
        self.rule = ContactValidationRule()

    def test_valid_contact_passes(self):
        data = {"email": "john.doe@gmail.com", "phone": "+91 98765 43210"}
        result = self.rule.evaluate(data, "")
        assert result.passed

    def test_missing_email_fails(self):
        data = {"phone": "+91 98765 43210"}
        result = self.rule.evaluate(data, "")
        assert not result.passed

    def test_disposable_email_fails(self):
        data = {"email": "user@mailinator.com", "phone": "9876543210"}
        result = self.rule.evaluate(data, "")
        assert not result.passed
        assert "mailinator" in result.evidence_snippet

    def test_malformed_email_fails(self):
        data = {"email": "not-an-email", "phone": "9876543210"}
        result = self.rule.evaluate(data, "")
        assert not result.passed


# ─────────────────────────────────────────────────────────────
# Resume Completeness Rule
# ─────────────────────────────────────────────────────────────

class TestResumeCompletenessRule:
    def setup_method(self):
        self.rule = ResumeCompletenessRule()

    def test_complete_resume_passes(self):
        data = {
            "skills": ["Python"],
            "education": [{"degree": "B.Tech"}],
            "experience": [{"company": "TechCorp", "description": "Built REST APIs and microservices"}],
            "email": "user@example.com",
        }
        # Use a long, diverse text well over the 80-word MIN_WORD_COUNT threshold
        text = (
            "Experienced Python developer with five years of expertise in Django REST framework and PostgreSQL. "
            "Delivered multiple enterprise projects involving microservices architecture, cloud deployments on AWS, "
            "and containerisation using Docker and Kubernetes. Strong background in API design, database optimisation "
            "with indexing strategies, and DevOps practices including Jenkins CI/CD pipelines and GitHub Actions. "
            "Collaborated closely with product managers, UX designers, and QA engineers to ship high-quality features "
            "on aggressive timelines. Introduced Redis caching that reduced API response times by forty percent. "
            "Mentored two junior developers, established coding standards, and led weekly technical review sessions."
        )
        result = self.rule.evaluate(data, text)
        assert result.passed

    def test_empty_resume_fails(self):
        result = self.rule.evaluate({}, "Too short.")
        assert not result.passed
        assert result.severity in ("MEDIUM", "HIGH")

    def test_missing_skills_section_fails(self):
        data = {
            "education": [{"degree": "B.Tech"}],
            "experience": [{"company": "TechCorp"}],
            "email": "user@example.com",
        }
        result = self.rule.evaluate(data, "word " * 100)
        assert not result.passed


# ─────────────────────────────────────────────────────────────
# Company Validation Rule
# ─────────────────────────────────────────────────────────────

class TestCompanyValidationRule:
    def setup_method(self):
        self.rule = CompanyValidationRule()

    def test_real_company_passes(self):
        data = {
            "experience": [
                {"company": "Infosys Limited", "start_date": "2019", "end_date": "2022"},
            ]
        }
        result = self.rule.evaluate(data, "")
        assert result.passed

    def test_placeholder_company_fails(self):
        data = {
            "experience": [
                {"company": "Company XYZ", "start_date": "2019", "end_date": "2022"},
            ]
        }
        result = self.rule.evaluate(data, "")
        assert not result.passed
        assert "Placeholder" in result.description

    def test_no_experience_passes_with_low_confidence(self):
        result = self.rule.evaluate({}, "")
        assert result.passed
        assert result.confidence <= 0.5


# ─────────────────────────────────────────────────────────────
# Certification Validation Rule
# ─────────────────────────────────────────────────────────────

class TestCertificationValidationRule:
    def setup_method(self):
        self.rule = CertificationValidationRule()

    def test_valid_cert_passes(self):
        data = {
            "certifications": [
                {
                    "name": "AWS Certified Solutions Architect",
                    "issuer": "Amazon Web Services",
                    "credential_id": "AWS-123456",
                    "expiry_date": "2026",
                }
            ]
        }
        result = self.rule.evaluate(data, "")
        assert result.passed

    def test_expired_cert_fails(self):
        data = {
            "certifications": [
                {
                    "name": "AWS Certified Developer",
                    "issuer": "Amazon Web Services",
                    "expiry_date": "2019",
                }
            ]
        }
        result = self.rule.evaluate(data, "")
        assert not result.passed
        assert "Expired" in result.description

    def test_no_issuer_fails(self):
        data = {
            "certifications": [
                {"name": "Some Random Certification"}
            ]
        }
        result = self.rule.evaluate(data, "")
        assert not result.passed

    def test_no_certifications_passes(self):
        result = self.rule.evaluate({}, "")
        assert result.passed


# ─────────────────────────────────────────────────────────────
# Full Engine Integration
# ─────────────────────────────────────────────────────────────

class TestRuleEngineIntegration:
    def test_clean_resume_produces_no_warnings(self):
        engine = ResumeFraudRuleEngine()
        data = {
            "email": "candidate@gmail.com",
            "phone": "9876543210",
            "name": "Ravi Kumar",
            "skills": ["Python", "Django", "REST APIs", "PostgreSQL", "Docker"],
            "education": [{"degree": "B.Tech in CS", "institution": "IIT Delhi"}],
            "experience": [
                {
                    "company": "Infosys",
                    "start_date": "2019",
                    "end_date": "2022",
                    "description": "Built microservices using Python and Django REST Framework.",
                }
            ],
            "certifications": [],
        }
        # Realistic, diverse resume text — no artificial repetition
        text = (
            "Ravi Kumar is a backend engineer with four years of experience at Infosys Limited. "
            "He specialises in Python, Django REST framework, PostgreSQL, and containerisation with Docker. "
            "He earned his B.Tech in Computer Science from IIT Delhi in 2019 and has consistently "
            "delivered scalable services for enterprise clients across fintech, e-commerce, and SaaS verticals. "
            "His contributions include designing RESTful APIs, optimising database queries, integrating "
            "third-party payment gateways, and implementing automated testing pipelines with pytest. "
            "He has mentored two junior engineers, conducted weekly code reviews, and improved deployment "
            "frequency from monthly to weekly releases through CI/CD adoption on GitHub Actions."
        )
        warnings = engine.evaluate(data, text)
        # A well-formed clean resume should produce 0 warnings
        assert len(warnings) == 0

    def test_suspicious_resume_produces_warnings(self):
        engine = ResumeFraudRuleEngine()
        data = {
            # No contact info
            "skills": [f"Skill{i}" for i in range(70)],  # inflated
            "experience": [
                {"company": "Company XYZ", "start_date": "2025", "end_date": "2019"},  # reversed
            ],
            "certifications": [
                {"name": "AWS Certified", "issuer": "", "expiry_date": "2018"},  # expired + no issuer
            ],
        }
        text = ("python " * 15 + "aws " * 15) * 3  # stuffed
        warnings = engine.evaluate(data, text)
        assert len(warnings) >= 3  # multiple rules should fire

    def test_isolated_rule_failure_does_not_stop_engine(self):
        """A broken rule must not prevent other rules from executing."""
        from apps.resume_trust.services.rules.base_rule import BaseResumeRule

        class BrokenRule(BaseResumeRule):
            RULE_CODE = "BROKEN_TEST"
            RULE_NAME = "Broken Test Rule"
            CATEGORY = "Test"
            DEFAULT_WEIGHT = 10

            def evaluate(self, parsed_data, raw_text):
                raise RuntimeError("Simulated rule crash")

        engine = ResumeFraudRuleEngine(rules=[BrokenRule(), ContactValidationRule()])
        data = {}  # missing contact — ContactValidation should fire
        warnings = engine.evaluate(data, "")
        # BrokenRule skipped, ContactValidationRule still ran and fired
        rule_codes = {w["rule_code"] for w in warnings}
        assert "CONTACT_001" in rule_codes
        assert "BROKEN_TEST" not in rule_codes

    def test_custom_rule_injection_without_modifying_engine(self):
        """Prove OCP: inject a brand-new rule without touching the engine."""
        from apps.resume_trust.services.rules.base_rule import BaseResumeRule

        class CustomRule(BaseResumeRule):
            RULE_CODE = "CUSTOM_001"
            RULE_NAME = "Custom Test Rule"
            CATEGORY = "Custom"
            DEFAULT_WEIGHT = 5

            def evaluate(self, parsed_data, raw_text):
                if "forbidden_keyword" in raw_text.lower():
                    return self._fail(
                        title="Forbidden keyword",
                        description="Text contains forbidden_keyword",
                        severity="LOW",
                    )
                return self._pass()

        engine = ResumeFraudRuleEngine(rules=[CustomRule()])
        warnings = engine.evaluate({}, "this resume has forbidden_keyword inside")
        assert len(warnings) == 1
        assert warnings[0]["rule_code"] == "CUSTOM_001"
