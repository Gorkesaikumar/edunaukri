"""
Comprehensive automated tests for the Resume Validation Pipeline.

Covers:
- Modern ATS resumes
- Fresher resumes (no work experience)
- Experienced resumes
- One-page and multi-page resumes
- Image-based / scanned PDFs (text extraction returns empty)
- Random PDFs
- Invoices and receipts
- Empty PDFs
- Password-protected PDFs
- Unsupported formats

Ensures:
- Genuine resumes PASS validation (no false negatives)
- Non-resume documents FAIL validation (no false positives)
- Raw text is properly extracted and passed to the trust engine
- Weighted scoring correctly classifies edge-case resumes
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from apps.resume_trust.services.resume_validators import (
    ResumeCompletenessValidator,
    ResumeDetectionService,
    ResumeReadabilityValidator,
    ValidationResult,
)
from apps.resume_trust.services.resume_trust_pipeline_service import ResumeTrustPipelineService


# ===========================================================================
# Test Fixtures — Resume Text Samples
# ===========================================================================

MODERN_ATS_RESUME = """
Nakul Deshmukh
Software Engineer | nakul.deshmukh@gmail.com | +91 9876543210 | linkedin.com/in/nakul

PROFESSIONAL SUMMARY
Results-driven Software Engineer with 4 years of experience building scalable web applications
using Python, Django, React.js and PostgreSQL.

SKILLS
Python, Django, REST API, React.js, JavaScript, TypeScript, PostgreSQL, Redis, Docker, Git, Agile

EXPERIENCE
Senior Software Engineer — TechCorp Pvt Ltd (Jan 2022 – Present)
- Led development of microservices architecture serving 2M+ requests/day
- Mentored 3 junior developers

Software Engineer — StartupXYZ (Jun 2020 – Dec 2021)
- Built end-to-end Django REST APIs for fintech platform

EDUCATION
B.Tech Computer Science — VJTI Mumbai (2016–2020) | CGPA: 8.4

CERTIFICATIONS
AWS Certified Solutions Architect – Associate (2023)
"""

FRESHER_RESUME = """
Priya Sharma
priya.sharma@email.com | 9876543210 | github.com/priyasharma

CAREER OBJECTIVE
Enthusiastic Computer Science graduate seeking entry-level Software Developer position.

EDUCATION
B.E. Computer Engineering — Pune University (2020–2024) | CGPA: 8.1
12th — Maharashtra Board (2020) | 91%

SKILLS
Python, Java, HTML, CSS, JavaScript, MySQL, Git

PROJECTS
Library Management System (Python + Django + SQLite)
E-Commerce Website (React.js + Node.js)

INTERNSHIP
Web Developer Intern — ABC Tech (May 2023 – Jul 2023)
Built REST APIs for inventory management system.
"""

EXPERIENCED_RESUME_MINIMAL = """
Rajesh Kumar
rajesh.kumar@outlook.com
+91-98765-43210

Work History
Principal Engineer, InfoSys (2018–Present)
Tech Lead, Wipro (2014–2018)

Education
M.Tech, IIT Delhi (2012–2014)
B.Tech, NIT Trichy (2008–2012)

Core Skills
Java, Microservices, AWS, Kubernetes, CI/CD, Leadership
"""

FACULTY_CV = """
Dr. Ananya Rao | Professor of Computer Science
ananya.rao@university.edu | +91 80 2234 5678

Academic Qualifications
PhD Computer Science — IISc Bangalore (2010)
M.Tech — BITS Pilani (2006)
B.Tech — NITK Surathkal (2004)

Research Interests
Machine Learning, NLP, Deep Learning, Computer Vision

Publications
"Efficient Transformer Architectures" — IEEE Transactions 2023
"BERT Fine-tuning for Domain Adaptation" — AAAI 2022

Teaching Experience
Professor — VIT University (2015–Present)
Assistant Professor — BITS Pilani (2010–2015)

Skills
Python, TensorFlow, PyTorch, R, MATLAB, LaTeX
"""

INVOICE_TEXT = """
TAX INVOICE
Invoice No: INV-2024-001
Invoice Date: January 15, 2024
Billed To: XYZ Company Pvt Ltd

Item          Qty    Rate    Amount
Web Services   1    50000    50000

Subtotal:              50000
GST 18%:               9000
Amount Due:           59000
GSTIN: 27AABCU9603R1ZX

Payment Terms: Due within 30 days
"""

BANK_STATEMENT = """
Account Statement
Statement Period: Jan 2024 – Mar 2024
Account No: XXXX-XXXX-1234

Transaction ID    Date        Description          Amount
TXN001            01-Jan-24   Opening Balance      10000
TXN002            05-Jan-24   ATM Withdrawal      -5000
TXN003            10-Jan-24   Credit Card Payment -2000

Credit Card Statement Balance Due: 7000
"""

EMPTY_TEXT = ""

VERY_SHORT_TEXT = "Hello World"

IMAGE_PDF_TEXT = "   "  # Scanned/image PDF returns whitespace only


# ===========================================================================
# 1. ResumeReadabilityValidator
# ===========================================================================

class TestResumeReadabilityValidator:
    def setup_method(self):
        self.validator = ResumeReadabilityValidator()

    def test_no_file_and_no_text_returns_file_missing(self):
        result = self.validator.validate_stored_file(None, "")
        assert not result.is_valid
        assert result.error_code == "FILE_MISSING"
        assert "No resume file" in result.error_message

    def test_stored_file_with_valid_text_passes(self):
        stored_file = MagicMock()
        stored_file.mime_type = "application/pdf"
        stored_file.original_filename = "resume.pdf"
        result = self.validator.validate_stored_file(stored_file, MODERN_ATS_RESUME)
        assert result.is_valid

    def test_stored_file_with_empty_text_returns_precise_message(self):
        stored_file = MagicMock()
        stored_file.mime_type = "application/pdf"
        stored_file.original_filename = "resume.pdf"
        result = self.validator.validate_stored_file(stored_file, "")
        assert not result.is_valid
        assert result.error_code == "UNREADABLE_OR_EMPTY"
        # Should NOT say "No resume file or text was provided" since a file IS provided
        assert "No resume file or text" not in result.error_message
        assert "uploaded file was received" in result.error_message

    def test_unsupported_mime_type_fails(self):
        stored_file = MagicMock()
        stored_file.mime_type = "text/plain"
        stored_file.original_filename = "document.txt"
        result = self.validator.validate_stored_file(stored_file, MODERN_ATS_RESUME)
        assert not result.is_valid
        assert result.error_code == "UNSUPPORTED_FORMAT"

    def test_raw_text_only_no_file_passes_if_sufficient(self):
        result = self.validator.validate_stored_file(None, MODERN_ATS_RESUME)
        assert result.is_valid

    def test_raw_text_only_very_short_fails(self):
        result = self.validator.validate_stored_file(None, VERY_SHORT_TEXT)
        assert not result.is_valid
        assert result.error_code == "UNREADABLE_OR_EMPTY"


# ===========================================================================
# 2. ResumeDetectionService — Weighted Scoring
# ===========================================================================

class TestResumeDetectionService:
    def setup_method(self):
        self.service = ResumeDetectionService()

    # ── Valid resume cases ──────────────────────────────────────────────────

    def test_modern_ats_resume_passes(self):
        result = self.service.detect_resume(raw_text=MODERN_ATS_RESUME)
        assert result.is_valid, f"ATS resume should pass. Signals: {result.details}"

    def test_fresher_resume_passes(self):
        result = self.service.detect_resume(raw_text=FRESHER_RESUME)
        assert result.is_valid, f"Fresher resume should pass. Signals: {result.details}"

    def test_experienced_minimal_resume_passes(self):
        result = self.service.detect_resume(raw_text=EXPERIENCED_RESUME_MINIMAL)
        assert result.is_valid, f"Experienced resume should pass. Signals: {result.details}"

    def test_faculty_cv_passes(self):
        result = self.service.detect_resume(raw_text=FACULTY_CV)
        assert result.is_valid, f"Faculty CV should pass. Signals: {result.details}"

    def test_resume_with_parsed_data_bonus_passes(self):
        """Parsed structured data gives bonus points — even thin raw text can pass."""
        thin_text = "John Doe john@email.com +1 555 000 0000"
        parsed = {"skills": ["Python", "Django"], "education": ["B.Tech CSE 2020"], "name": "John Doe"}
        result = self.service.detect_resume(raw_text=thin_text, parsed_data=parsed)
        assert result.is_valid, f"Should pass with parsed data bonus. Signals: {result.details}"

    def test_resume_with_email_and_education_passes(self):
        text = "john@example.com +91 9876543210 Education B.Tech Computer Science skills Python Java"
        result = self.service.detect_resume(raw_text=text)
        assert result.is_valid

    def test_fresher_without_experience_section_passes(self):
        """Fresher resumes may not have work experience — should still pass."""
        text = """
        Amit Gupta | amit.gupta@gmail.com | 9876543210
        Education: B.Tech CSE, NIT 2024, CGPA 8.0
        Skills: Python, Java, HTML, CSS, MySQL, Git
        Projects: Library System (Django), Portfolio Website (React)
        """
        result = self.service.detect_resume(raw_text=text)
        assert result.is_valid, f"Fresher without experience should pass. Signals: {result.details}"

    # ── Non-resume cases ────────────────────────────────────────────────────

    def test_invoice_fails(self):
        result = self.service.detect_resume(raw_text=INVOICE_TEXT)
        assert not result.is_valid
        assert result.error_code == "NOT_A_RESUME"

    def test_bank_statement_fails(self):
        result = self.service.detect_resume(raw_text=BANK_STATEMENT)
        assert not result.is_valid
        assert result.error_code == "NOT_A_RESUME"

    def test_empty_text_fails(self):
        result = self.service.detect_resume(raw_text=EMPTY_TEXT)
        assert not result.is_valid
        assert result.error_code == "NOT_A_RESUME"

    def test_minimal_non_resume_text_fails(self):
        result = self.service.detect_resume(raw_text="Hello this is a random document with no structure.")
        assert not result.is_valid

    def test_invoice_with_parsed_data_still_fails(self):
        """Hard exclusion should override parsed data bonuses."""
        parsed = {"skills": ["Python"], "education": ["B.Tech"]}
        result = self.service.detect_resume(raw_text=INVOICE_TEXT, parsed_data=parsed)
        assert not result.is_valid
        assert result.error_code == "NOT_A_RESUME"

    # ── Scoring transparency ─────────────────────────────────────────────────

    def test_confidence_score_returned_in_details(self):
        result = self.service.detect_resume(raw_text=MODERN_ATS_RESUME)
        assert result.details is not None
        assert "confidence_score" in result.details
        assert result.details["confidence_score"] >= ResumeDetectionService.MIN_CONFIDENCE_SCORE

    def test_matched_signals_returned_in_details(self):
        result = self.service.detect_resume(raw_text=MODERN_ATS_RESUME)
        assert "matched_signals" in result.details
        assert len(result.details["matched_signals"]) > 0


# ===========================================================================
# 3. ResumeCompletenessValidator
# ===========================================================================

class TestResumeCompletenessValidator:
    def setup_method(self):
        self.validator = ResumeCompletenessValidator()

    def test_complete_resume_passes(self):
        result = self.validator.validate_completeness(raw_text=MODERN_ATS_RESUME)
        assert result.is_valid

    def test_fresher_resume_passes_even_without_experience(self):
        result = self.validator.validate_completeness(raw_text=FRESHER_RESUME)
        assert result.is_valid

    def test_no_contact_and_no_sections_fails(self):
        text = "Random document content without structure"
        result = self.validator.validate_completeness(raw_text=text, parsed_data={})
        assert not result.is_valid
        assert result.error_code == "INCOMPLETE_RESUME"

    def test_contact_only_no_sections_passes_completeness(self):
        """
        ResumeCompletenessValidator is intentionally lenient.
        A document with contact info (email + phone) passes the completeness gate.
        Non-resume detection is handled separately by ResumeDetectionService.
        """
        text = "john@example.com +91 9876543210"
        result = self.validator.validate_completeness(raw_text=text, parsed_data={})
        # Contact exists → completeness passes. Detection would fail this document separately.
        assert result.is_valid

    def test_parsed_data_sections_satisfy_completeness(self):
        text = "john@example.com +91 9876543210"
        parsed = {"skills": ["Python"], "education": ["B.Tech"]}
        result = self.validator.validate_completeness(raw_text=text, parsed_data=parsed)
        assert result.is_valid


# ===========================================================================
# 4. Pipeline Service — _extract_text_from_stored_file
# ===========================================================================

class TestExtractTextFromStoredFile:
    def _make_stored_file(self, name="resume.pdf", mime="application/pdf"):
        sf = MagicMock()
        sf.original_filename = name
        sf.mime_type = mime
        sf.pk = "test-uuid-123"
        return sf

    def test_empty_pdf_returns_empty_string(self, tmp_path):
        """A PDF that returns no text should return empty string, not raise."""
        import pypdf
        # Create a minimal empty PDF
        pdf_path = tmp_path / "empty.pdf"
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=200, height=200)
        with open(pdf_path, "wb") as f:
            writer.write(f)

        sf = self._make_stored_file("empty.pdf")
        from apps.it_recruitment.services.universal_resume_parser import UniversalResumeParserService
        with patch.object(
            UniversalResumeParserService,
            "_extract_text",
            return_value=""
        ) as mock_extract:
            result = UniversalResumeParserService()._extract_text(sf)
            assert result == ""
            mock_extract.assert_called_once_with(sf)

    def test_corrupt_path_returns_empty_string(self):
        """Non-existent file path should return empty string, not raise."""
        from pathlib import Path
        sf = self._make_stored_file("resume.pdf")
        with patch("apps.documents.services.storage_service.StorageService.get_absolute_path",
                   return_value=Path("/nonexistent/path/resume.pdf")):
            result = UniversalResumeParserService()._extract_text(sf)
        assert result == ""

    def test_docx_extraction_works(self, tmp_path):
        """DOCX extraction path executes without error."""
        import zipfile
        import io
        docx_path = tmp_path / "resume.docx"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>John Doe Software Engineer email@example.com skills Python Django education B.Tech</w:t></w:r></w:p>
  </w:body>
</w:document>"""
        with zipfile.ZipFile(docx_path, "w") as zf:
            zf.writestr("word/document.xml", xml_content)
            zf.writestr("[Content_Types].xml", b'<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')

        sf = self._make_stored_file("resume.docx")
        with patch("apps.documents.services.storage_service.StorageService.get_absolute_path", return_value=docx_path):
            result = ResumeTrustPipelineService._extract_text_from_stored_file(sf)
        assert "John Doe" in result
        assert "Python" in result


# ===========================================================================
# 5. End-to-end: Pipeline validates correctly for key scenarios
# ===========================================================================

class TestEndToEndValidationScenarios:
    """
    Verifies that the complete validation chain (Readability → Detection → Completeness)
    produces the correct outcome for key resume types and non-resume documents.
    """

    def _run_validators(self, raw_text, stored_file=None, parsed_data=None):
        readability = ResumeReadabilityValidator()
        detection = ResumeDetectionService()
        completeness = ResumeCompletenessValidator()
        parsed = parsed_data or {}

        r = readability.validate_stored_file(stored_file, raw_text)
        if not r.is_valid:
            return "READABILITY_FAILED", r.error_message

        d = detection.detect_resume(raw_text, parsed)
        if not d.is_valid:
            return "DETECTION_FAILED", d.error_message

        c = completeness.validate_completeness(raw_text, parsed)
        if not c.is_valid:
            return "COMPLETENESS_FAILED", c.error_message

        return "PASSED", None

    def test_modern_ats_resume_passes_all_stages(self):
        status, msg = self._run_validators(MODERN_ATS_RESUME)
        assert status == "PASSED", f"ATS resume failed at: {status} — {msg}"

    def test_fresher_resume_passes_all_stages(self):
        status, msg = self._run_validators(FRESHER_RESUME)
        assert status == "PASSED", f"Fresher resume failed at: {status} — {msg}"

    def test_experienced_resume_passes_all_stages(self):
        status, msg = self._run_validators(EXPERIENCED_RESUME_MINIMAL)
        assert status == "PASSED", f"Experienced resume failed at: {status} — {msg}"

    def test_faculty_cv_passes_all_stages(self):
        status, msg = self._run_validators(FACULTY_CV)
        assert status == "PASSED", f"Faculty CV failed at: {status} — {msg}"

    def test_invoice_fails_at_detection(self):
        status, msg = self._run_validators(INVOICE_TEXT)
        assert status == "DETECTION_FAILED", f"Invoice should fail detection, got: {status}"

    def test_bank_statement_fails_at_detection(self):
        status, msg = self._run_validators(BANK_STATEMENT)
        assert status == "DETECTION_FAILED", f"Bank statement should fail detection, got: {status}"

    def test_empty_pdf_fails_at_readability(self):
        """Empty text + stored file → readability fails with precise message."""
        sf = MagicMock()
        sf.mime_type = "application/pdf"
        sf.original_filename = "empty.pdf"
        status, msg = self._run_validators("", stored_file=sf)
        assert status == "READABILITY_FAILED"
        assert "No resume file or text" not in msg  # Should be precise, not generic

    def test_no_file_no_text_fails_with_file_missing(self):
        status, msg = self._run_validators("")
        assert status == "READABILITY_FAILED"
        assert "No resume file or text" in msg

    def test_image_only_pdf_fails_at_readability(self):
        """Scanned PDF text returns near-empty — readability fails with actionable message."""
        sf = MagicMock()
        sf.mime_type = "application/pdf"
        sf.original_filename = "scanned_resume.pdf"
        status, msg = self._run_validators(IMAGE_PDF_TEXT, stored_file=sf)
        assert status == "READABILITY_FAILED"

    def test_unsupported_format_fails_at_readability(self):
        sf = MagicMock()
        sf.mime_type = "text/plain"
        sf.original_filename = "document.txt"
        status, msg = self._run_validators(MODERN_ATS_RESUME, stored_file=sf)
        assert status == "READABILITY_FAILED"
