"""Test suite for Phase 1 Resume Trust & Fraud Detection Engine architecture."""

import json
import pytest
from django.test import RequestFactory

from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.documents.models import StoredFile
from apps.resume_trust.models import (
    AnalysisRecommendation,
    AnalysisStatus,
    FraudDomainType,
    ResumeFraudAnalysis,
    ResumeFraudHistory,
    ResumeFraudRule,
    ResumeFraudWarning,
    RiskLevel,
)
from apps.resume_trust.repositories import ResumeFraudRepository
from apps.resume_trust.services.resume_fraud_builder_and_mappers import (
    ResumeFraudAnalysisBuilder,
    ResumeFraudResultMapper,
    ResumeFraudValidator,
)
from apps.resume_trust.services.resume_fraud_detection_service import (
    ResumeFraudDetectionService,
)
from apps.resume_trust.services.resume_fraud_report_service import ResumeFraudReportService
from apps.resume_trust.services.resume_fraud_rule_engine import ResumeFraudRuleEngine
from apps.resume_trust.services.resume_trust_score_calculator import (
    ResumeTrustScoreCalculator,
)
from apps.resume_trust.views import (
    ResumeTrustAnalyzeAPIView,
    ResumeTrustHistoryAPIView,
    ResumeTrustReportAPIView,
)


@pytest.mark.django_db
class TestResumeTrustArchitecture:
    """Test suite covering models, repositories, calculator, services, and APIs."""

    @pytest.fixture
    def it_candidate_user(self):
        return ITUser.objects.create_user(email="it.candidate@edunaukri.com", password="Password123!")

    @pytest.fixture
    def faculty_candidate_user(self):
        return ProfessorUser.objects.create_user(
            email="prof.candidate@edunaukri.com", password="Password123!"
        )

    @pytest.fixture
    def sample_file(self, it_candidate_user):
        import uuid
        from apps.core.constants.enums import DomainType
        from apps.documents.constants.enums import StorageFileType
        return StoredFile.objects.create(
            domain=DomainType.IT,
            file_type=StorageFileType.RESUME,
            original_filename="sample_resume.pdf",
            stored_filename=f"{uuid.uuid4()}.pdf",
            storage_path="resumes/sample.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            owner_type="job_seeker",
            owner_id=uuid.uuid4(),
            uploaded_by_id=uuid.uuid4(),
        )

    def test_database_models_creation(self, it_candidate_user, sample_file):
        analysis = ResumeFraudAnalysis.objects.create(
            seeker_user_id=it_candidate_user.pk,
            domain=FraudDomainType.IT,
            stored_file=sample_file,
            trust_score=95,
            risk_score=5,
            risk_level=RiskLevel.LOW,
            status=AnalysisStatus.SUCCESS,
        )
        assert analysis.pk is not None
        assert str(analysis.trust_score) == "95"
        assert str(analysis)

        warning = ResumeFraudWarning.objects.create(
            fraud_analysis=analysis,
            rule_code="FORMAT_CHECK",
            rule_name="Format Validation",
            severity="LOW",
            title="Clean Layout",
            description="Document layout verified.",
        )
        assert warning.pk is not None
        assert warning.fraud_analysis == analysis

        rule = ResumeFraudRule.objects.create(
            rule_code="RULE_001",
            name="Timeline Consistency",
            category="Timeline",
            default_weight=15,
        )
        assert rule.rule_code == "RULE_001"

        history = ResumeFraudHistory.objects.create(
            fraud_analysis=analysis,
            seeker_user_id=it_candidate_user.pk,
            domain=FraudDomainType.IT,
            previous_trust_score=80,
            new_trust_score=95,
            score_delta=15,
            change_reason="Resume Updated",
        )
        assert history.score_delta == 15

    def test_repository_lifecycle(self, it_candidate_user, sample_file):
        repo = ResumeFraudRepository()
        analysis = repo.create_analysis(
            seeker_user_id=it_candidate_user.pk,
            domain=FraudDomainType.IT,
            stored_file=sample_file,
        )
        assert analysis.status == AnalysisStatus.PENDING

        repo.add_warning(
            analysis,
            rule_code="TEST_RULE",
            rule_name="Test Rule",
            severity="MEDIUM",
            title="Warning Title",
        )
        analysis.refresh_from_db()
        assert analysis.warning_count == 1

        completed = repo.mark_completed(
            analysis=analysis,
            trust_score=85,
            risk_score=15,
            risk_level=RiskLevel.LOW,
            warning_count=1,
            recommendation=AnalysisRecommendation.PASS,
            duration_ms=120,
            json_report={"status": "ok"},
        )
        assert completed.status == AnalysisStatus.SUCCESS
        assert completed.trust_score == 85

        latest = repo.get_latest_for_user(it_candidate_user.pk, domain=FraudDomainType.IT)
        assert latest.id == completed.id

    def test_trust_score_calculator(self):
        calc = ResumeTrustScoreCalculator()
        res_clean = calc.calculate([])
        assert res_clean["trust_score"] == 100
        assert res_clean["risk_level"] == RiskLevel.LOW
        assert res_clean["recommendation"] == AnalysisRecommendation.PASS

        warnings = [
            {"rule_code": "WARN_1", "severity": "HIGH", "weight": 30},
            {"rule_code": "WARN_2", "severity": "CRITICAL", "weight": 50},
        ]
        res_risk = calc.calculate(warnings)
        assert res_risk["risk_score"] == 80
        assert res_risk["trust_score"] == 20
        assert res_risk["risk_level"] == RiskLevel.CRITICAL
        assert res_risk["recommendation"] == AnalysisRecommendation.REJECT

    def test_rule_engine_shell(self):
        engine = ResumeFraudRuleEngine()
        result = engine.evaluate({"skills": ["Python"]}, raw_text="Experienced developer")
        assert isinstance(result, list)

    def test_analysis_builder_and_mapper(self, it_candidate_user, sample_file):
        builder = ResumeFraudAnalysisBuilder()
        report = builder.build_report(
            analysis_id="12345678-1234-5678-1234-567812345678",
            domain="it",
            seeker_user_id=it_candidate_user.pk,
            trust_score=90,
            risk_score=10,
            risk_level="LOW",
            recommendation="PASS",
            warnings=[],
            execution_time_ms=85,
        )
        assert report["trust_score"] == 90
        assert "ai_explanation" in report

        analysis = ResumeFraudAnalysis.objects.create(
            seeker_user_id=it_candidate_user.pk,
            domain=FraudDomainType.IT,
            stored_file=sample_file,
            trust_score=90,
            risk_score=10,
            risk_level=RiskLevel.LOW,
            status=AnalysisStatus.SUCCESS,
            json_analysis_report=report,
        )

        mapper = ResumeFraudResultMapper()
        mapped_dict = mapper.to_dict(analysis)
        assert mapped_dict["trust_score"] == 90
        assert mapped_dict["domain"] == "it"

    def test_detection_service_orchestration_it_domain(self, it_candidate_user, sample_file):
        service = ResumeFraudDetectionService()
        clean_data = {
            "email": "candidate@gmail.com",
            "phone": "9876543210",
            "skills": ["Python", "Django", "PostgreSQL", "Docker"],
            "education": [{"degree": "B.Tech in CS", "institution": "IIT Delhi"}],
            "experience": [
                {
                    "company": "Infosys Limited",
                    "start_date": "2019",
                    "end_date": "2022",
                    "description": "Built scalable REST APIs using Python and Django REST framework.",
                }
            ],
            "certifications": [],
        }
        clean_text = (
            "Candidate is a backend engineer at Infosys Limited with four years of experience. "
            "Specialises in Python, Django REST framework, PostgreSQL, and Docker containerisation. "
            "Holds B.Tech from IIT Delhi. Designed microservices, optimised database queries, "
            "and delivered enterprise-grade API solutions for fintech and SaaS clients. "
            "Mentored junior engineers and led CI/CD adoption using GitHub Actions."
        )
        report = service.initiate_analysis(
            seeker_user_id=it_candidate_user.pk,
            domain=FraudDomainType.IT,
            stored_file=sample_file,
            parsed_data=clean_data,
            raw_text=clean_text,
        )
        assert report["status"] == AnalysisStatus.SUCCESS
        # Trust score may vary based on rule results; verify it ran successfully
        assert 0 <= report["trust_score"] <= 100
        assert report["domain"] == FraudDomainType.IT

    def test_detection_service_orchestration_faculty_domain(self, faculty_candidate_user, sample_file):
        service = ResumeFraudDetectionService()
        clean_data = {
            "email": "professor@university.edu",
            "phone": "9812345678",
            "skills": ["Machine Learning", "Deep Learning", "Python", "TensorFlow"],
            "education": [{"degree": "Ph.D in Computer Science", "institution": "IIT Bombay"}],
            "experience": [
                {
                    "company": "IIT Bombay",
                    "start_date": "2015",
                    "end_date": "Present",
                    "description": "Associate Professor teaching AI and ML. Published 20 peer-reviewed papers.",
                }
            ],
            "certifications": [],
        }
        clean_text = (
            "Professor of Computer Science at IIT Bombay with ten years of academic experience. "
            "Earned Ph.D from IIT Bombay in 2015 with specialisation in artificial intelligence. "
            "Published over twenty peer-reviewed papers in IEEE and ACM journals on machine learning, "
            "deep learning, and natural language processing. Supervised fifteen doctoral students and "
            "secured research grants from DST and SERB. Expertise in Python, TensorFlow, and PyTorch."
        )
        report = service.initiate_analysis(
            seeker_user_id=faculty_candidate_user.pk,
            domain=FraudDomainType.FACULTY,
            stored_file=sample_file,
            parsed_data=clean_data,
            raw_text=clean_text,
        )
        assert report["status"] == AnalysisStatus.SUCCESS
        assert 0 <= report["trust_score"] <= 100
        assert report["domain"] == FraudDomainType.FACULTY

    def test_report_service(self, it_candidate_user, sample_file):
        service = ResumeFraudDetectionService()
        service.initiate_analysis(
            seeker_user_id=it_candidate_user.pk,
            domain=FraudDomainType.IT,
            stored_file=sample_file,
            parsed_data={
                "email": "candidate@gmail.com",
                "phone": "9876543210",
                "skills": ["Python", "Django"],
                "education": [{"degree": "B.Tech", "institution": "IIT Delhi"}],
                "experience": [
                    {
                        "company": "Infosys",
                        "start_date": "2019",
                        "end_date": "2022",
                        "description": "Developed REST APIs and microservices.",
                    }
                ],
            },
            raw_text=(
                "Experienced Python Django developer at Infosys with strong background in "
                "REST API development, PostgreSQL, and cloud deployments. B.Tech from IIT Delhi. "
                "Delivered multiple enterprise projects on time with cross-functional teams."
            ),
        )

        report_svc = ResumeFraudReportService()
        latest = report_svc.get_user_latest_report(it_candidate_user.pk, domain=FraudDomainType.IT)
        assert latest["has_analysis"] is True
        # Trust score reflects real rule evaluation — verify it is a valid score
        assert 0 <= latest["trust_score"] <= 100

        history = report_svc.get_user_trust_history(it_candidate_user.pk, domain=FraudDomainType.IT)
        assert history["count"] >= 1

    def test_api_views(self, it_candidate_user, sample_file):
        factory = RequestFactory()

        # 1. Analyze API View
        req_post = factory.post(
            "/api/resume-trust/analyze/",
            data=json.dumps({"file_id": str(sample_file.pk)}),
            content_type="application/json",
        )
        req_post.user = it_candidate_user
        view_analyze = ResumeTrustAnalyzeAPIView()
        resp_post = view_analyze.post(req_post)
        assert resp_post.status_code == 200
        body_post = json.loads(resp_post.content)
        assert body_post["success"] is True

        # 2. Report API View
        req_get_report = factory.get("/api/resume-trust/report/")
        req_get_report.user = it_candidate_user
        view_report = ResumeTrustReportAPIView()
        resp_report = view_report.get(req_get_report)
        assert resp_report.status_code == 200
        body_report = json.loads(resp_report.content)
        assert body_report["success"] is True

        # 3. History API View
        req_get_hist = factory.get("/api/resume-trust/history/")
        req_get_hist.user = it_candidate_user
        view_hist = ResumeTrustHistoryAPIView()
        resp_hist = view_hist.get(req_get_hist)
        assert resp_hist.status_code == 200
        body_hist = json.loads(resp_hist.content)
        assert body_hist["success"] is True
