"""Unit test suite for Phase 2 Resume Trust automated pipeline integration."""

import pytest
from unittest.mock import MagicMock, patch

from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.academic_recruitment.models.professor import ProfessorProfile
from apps.academic_recruitment.tasks import parse_faculty_resume_task
from apps.documents.constants.enums import StorageFileType
from apps.documents.models import StoredFile
from apps.it_recruitment.models import JobSeekerProfile
from apps.it_recruitment.tasks import parse_resume_task
from apps.resume_trust.models import AnalysisStatus, FraudDomainType, ResumeFraudAnalysis
from apps.resume_trust.services.resume_placeholder_analyzer import ResumePlaceholderAnalyzer
from apps.resume_trust.services.resume_trust_pipeline_service import ResumeTrustPipelineService


@pytest.mark.django_db
class TestResumeTrustPipeline:
    """Test suite covering the 5-step automated resume pipeline for IT & Faculty domains."""

    @pytest.fixture
    def it_seeker(self):
        user = ITUser.objects.create_user(email="it.pipeline@edunaukri.com", password="Password123!")
        profile = JobSeekerProfile.objects.create(
            user=user,
            first_name="Praveen",
            last_name="Kumar",
        )
        return user, profile

    @pytest.fixture
    def faculty_seeker(self):
        user = ProfessorUser.objects.create_user(email="faculty.pipeline@edunaukri.com", password="Password123!")
        profile = ProfessorProfile.objects.create(
            user=user,
            first_name="Dr. Sunita",
            last_name="Rao",
        )
        return user, profile

    @pytest.fixture
    def sample_file(self, it_seeker):
        user, _ = it_seeker
        import uuid
        from apps.core.constants.enums import DomainType
        return StoredFile.objects.create(
            domain=DomainType.IT,
            file_type=StorageFileType.RESUME,
            original_filename="candidate_cv.pdf",
            stored_filename=f"{uuid.uuid4()}.pdf",
            storage_path="resumes/test.pdf",
            mime_type="application/pdf",
            file_size_bytes=2048,
            owner_type="job_seeker",
            owner_id=user.pk,
            uploaded_by_id=user.pk,
        )

    def test_placeholder_analyzer(self, sample_file):
        analyzer = ResumePlaceholderAnalyzer()
        signals = analyzer.get_all_placeholder_signals(sample_file, raw_text="Sample Resume Text")
        assert len(signals) == 3
        assert signals[0]["is_valid_format"] is True

    @patch("apps.it_recruitment.services.resume_parsing_service.ResumeParsingService.parse_and_store")
    @patch("apps.it_recruitment.services.jobseeker_resume_analysis_service.JobSeekerResumeAnalysisService.get_analysis")
    @patch.object(ResumeTrustPipelineService, "_extract_text_from_stored_file", return_value="Praveen Kumar Email: praveen@gmail.com Phone: 9876543210 Education: BTech Computer Science Skills: Python Django Experience: Software Engineer 5 years")
    def test_it_domain_pipeline_execution(self, mock_extract, mock_get_analysis, mock_parse, it_seeker, sample_file):
        user, profile = it_seeker
        mock_parse.return_value = None
        mock_get_analysis.return_value = None

        pipeline = ResumeTrustPipelineService()
        result = pipeline.execute_pipeline(
            profile=profile,
            stored_file=sample_file,
            domain=FraudDomainType.IT,
        )

        assert result["status"] == "success"
        assert result["domain"] == FraudDomainType.IT
        assert result["user_id"] == str(user.pk)

        analysis = ResumeFraudAnalysis.objects.filter(
            seeker_user_id=str(user.pk), domain=FraudDomainType.IT
        ).first()
        assert analysis is not None
        assert analysis.status == AnalysisStatus.SUCCESS
        assert 0 <= analysis.trust_score <= 100  # score reflects actual rule evaluation

    @patch.object(ResumeTrustPipelineService, "_extract_text_from_stored_file", return_value="Dr. Sunita Rao Email: sunita@univ.edu Phone: 9876543210 Education: Ph.D Computer Science Skills: AI Machine Learning Experience: Professor 10 years")
    def test_faculty_domain_pipeline_execution(self, mock_pdf, faculty_seeker, sample_file):
        user, profile = faculty_seeker
        pipeline = ResumeTrustPipelineService()

        result = pipeline.execute_pipeline(
            profile=profile,
            stored_file=sample_file,
            domain=FraudDomainType.FACULTY,
        )

        assert result["status"] == "success"
        assert result["domain"] == FraudDomainType.FACULTY
        assert result["user_id"] == str(user.pk)

        analysis = ResumeFraudAnalysis.objects.filter(
            seeker_user_id=str(user.pk), domain=FraudDomainType.FACULTY
        ).first()
        assert analysis is not None
        assert analysis.status == AnalysisStatus.SUCCESS

    def test_transactional_rollback_on_failure(self, it_seeker, sample_file):
        user, profile = it_seeker
        pipeline = ResumeTrustPipelineService()

        with patch.object(pipeline.fraud_service, "initiate_analysis", side_effect=RuntimeError("Engine Failure")):
            with pytest.raises(RuntimeError):
                pipeline.execute_pipeline(
                    profile=profile,
                    stored_file=sample_file,
                    domain=FraudDomainType.IT,
                )

        # Confirm analysis was rolled back
        count = ResumeFraudAnalysis.objects.filter(seeker_user_id=str(user.pk)).count()
        assert count == 0

    @patch("apps.resume_trust.services.resume_trust_pipeline_service.ResumeTrustPipelineService.execute_pipeline")
    def test_celery_task_integration_it(self, mock_pipeline, it_seeker, sample_file):
        user, profile = it_seeker
        mock_pipeline.return_value = {"status": "success", "trust_report": {}}

        res = parse_resume_task(str(sample_file.pk), str(profile.pk))
        assert res["status"] == "ok"
        assert mock_pipeline.called

    @patch("apps.resume_trust.services.resume_trust_pipeline_service.ResumeTrustPipelineService.execute_pipeline")
    def test_celery_task_integration_faculty(self, mock_pipeline, faculty_seeker, sample_file):
        user, profile = faculty_seeker
        mock_pipeline.return_value = {"status": "success", "trust_report": {}}

        res = parse_faculty_resume_task(profile.pk, sample_file.pk)
        assert res["status"] == "success"
        assert mock_pipeline.called
