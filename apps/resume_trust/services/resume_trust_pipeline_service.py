"""Master pipeline orchestrator service for automated 5-step Resume Trust Engine pipeline."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from django.db import transaction

from apps.core.services.base import BaseService
from apps.resume_trust.models import FraudDomainType
from apps.resume_trust.services.resume_fraud_detection_service import ResumeFraudDetectionService
from apps.resume_trust.services.resume_placeholder_analyzer import ResumePlaceholderAnalyzer

logger = logging.getLogger("resume_trust")


class ResumeTrustPipelineService(BaseService):
    """Orchestrates the automated 5-step pipeline for IT and Faculty job seeker resume uploads:

    Step 1: Resume Upload (verification & versioning)
    Step 2: Resume Parsing (extract raw text, skills, education)
    Step 3: AI Resume Analysis (extract strengths, gaps, ATS score)
    Step 4: Resume Trust Engine (execute trust & fraud analysis, store analysis)
    Step 5: Update Dashboard (recalculate profile completeness & refresh candidate recommendations)
    """

    def __init__(
        self,
        fraud_service: Optional[ResumeFraudDetectionService] = None,
        placeholder_analyzer: Optional[ResumePlaceholderAnalyzer] = None,
    ):
        self.fraud_service = fraud_service or ResumeFraudDetectionService()
        self.placeholder_analyzer = placeholder_analyzer or ResumePlaceholderAnalyzer()

    @transaction.atomic
    def execute_pipeline(
        self,
        profile,
        stored_file,
        domain: str = FraudDomainType.IT,
        resume_version: int = 1,
    ) -> Dict[str, Any]:
        """Execute the automated 5-step pipeline wrapped in a single database transaction."""
        user_id = profile.user_id if hasattr(profile, "user_id") else profile.user.pk
        logger.info(
            "Executing Resume Pipeline | Domain: %s | User: %s | File: %s",
            domain,
            user_id,
            getattr(stored_file, "pk", None),
        )

        parsed_data = {}
        raw_text = ""

        # Step 1: Resume Upload verification
        if not stored_file:
            raise ValueError("Pipeline execution failed: No stored file provided.")

        logger.info(
            "Pipeline Step 1 PASSED: Resume file verified | Domain: %s | User: %s | File: %s | Size: %s bytes",
            domain, user_id, getattr(stored_file, "pk", None), getattr(stored_file, "file_size", "?"),
        )

        # Step 2: Resume Parsing — extract raw text and structured data
        if domain == FraudDomainType.IT:
            from apps.it_recruitment.services.resume_parsing_service import ResumeParsingService

            logger.info("Pipeline Step 2 START: Parsing IT resume for user %s", user_id)
            parsing_result = ResumeParsingService().parse_and_store(stored_file, profile=profile)
            parsed_data = ResumeParsingService().get_extracted(stored_file) or {}

            # CRITICAL FIX: raw_text is NOT stored on StoredFile model.
            # Re-extract it directly from the file after parse_and_store has verified storage is working.
            raw_text = self._extract_text_from_stored_file(stored_file)

            if not raw_text and parsed_data.get("text_length", 0) == 0:
                logger.warning(
                    "Pipeline Step 2 WARNING: Text extraction returned empty for user %s | File: %s",
                    user_id, getattr(stored_file, "pk", None),
                )
            else:
                logger.info(
                    "Pipeline Step 2 PASSED: Text extracted | User: %s | Length: %d chars | Skills: %s | Edu: %s | Exp: %s",
                    user_id, len(raw_text),
                    bool(parsed_data.get("skills")),
                    bool(parsed_data.get("education")),
                    bool(parsed_data.get("experience")),
                )

        else:
            # Faculty Domain Parsing
            from apps.academic_recruitment.models.resume import ParsedResume, ParsedResumeStatus

            logger.info("Pipeline Step 2 START: Parsing Faculty CV for user %s", user_id)
            parsed_resume, _ = ParsedResume.objects.get_or_create(profile=profile, cv_file=stored_file)
            parsed_resume.status = ParsedResumeStatus.PROCESSING
            parsed_resume.save(update_fields=["status"])

            raw_text = self._extract_text_from_stored_file(stored_file)
            parsed_resume.raw_text = raw_text
            parsed_resume.status = ParsedResumeStatus.SUCCESS
            parsed_resume.save(update_fields=["status", "raw_text"])

            parsed_data = {
                "skills": getattr(parsed_resume, "extracted_skills", []),
                "education": getattr(parsed_resume, "extracted_education", []),
            }

            logger.info(
                "Pipeline Step 2 PASSED: Faculty CV text extracted | User: %s | Length: %d chars",
                user_id, len(raw_text),
            )

        # Step 3: AI Resume Analysis
        logger.info("Pipeline Step 3 START: AI Resume Analysis for user %s | Domain: %s", user_id, domain)
        if domain == FraudDomainType.IT:
            from apps.it_recruitment.services.jobseeker_resume_analysis_service import (
                JobSeekerResumeAnalysisService,
            )
            JobSeekerResumeAnalysisService().get_analysis(profile, force_refresh=True)
            logger.info("Pipeline Step 3 PASSED: AI Resume Analysis completed for user %s", user_id)

        # Placeholder analyzer baseline check
        placeholder_signals = self.placeholder_analyzer.get_all_placeholder_signals(
            stored_file, raw_text=raw_text
        )
        parsed_data["_placeholder_signals"] = placeholder_signals

        logger.info(
            "Pipeline Step 4 START: Resume Trust Engine scan | User: %s | raw_text_len: %d",
            user_id, len(raw_text),
        )

        # Step 4 & Store Analysis: Resume Trust Engine Scan & Save
        trust_report = self.fraud_service.initiate_analysis(
            seeker_user_id=user_id,
            domain=domain,
            stored_file=stored_file,
            parsed_data=parsed_data,
            raw_text=raw_text,
            resume_version=resume_version,
        )

        logger.info(
            "Pipeline Step 4 PASSED: Trust Engine completed | User: %s | Status: %s | Score: %s | Risk: %s",
            user_id,
            trust_report.get("status"),
            trust_report.get("trust_score"),
            trust_report.get("risk_level"),
        )


        # Step 5: Update Dashboard & Recalculate Profile Completeness
        if domain == FraudDomainType.IT:
            from apps.it_recruitment.services.jobseeker_profile_manage_service import (
                JobSeekerProfileManageService,
            )
            from apps.it_recruitment.services.job_recommendation_engine_service import (
                JobRecommendationEngineService,
            )
            from apps.it_recruitment.services.job_recommendation_cache_service import (
                JobRecommendationCacheService,
            )

            JobSeekerProfileManageService().completion_service.recalculate(profile)
            if trust_report.get("status") == "SUCCESS":
                JobRecommendationEngineService().rebuild_for_seeker(
                    profile.pk, reason="resume_trust_pipeline_completed", notify=False
                )
            else:
                JobRecommendationCacheService().clear_cache(profile)
        else:
            from apps.academic_recruitment.services.professor_profile_completion_service import (
                ProfessorProfileCompletionService,
            )

            ProfessorProfileCompletionService().recalculate(profile)

        logger.info(
            "Resume Pipeline Completed Successfully | Domain: %s | User: %s | TrustScore: %s",
            domain,
            user_id,
            trust_report.get("trust_score"),
        )

        return {
            "status": "success",
            "domain": domain,
            "user_id": str(user_id),
            "stored_file_id": str(stored_file.pk),
            "trust_report": trust_report,
        }

    @staticmethod
    def _extract_text_from_stored_file(stored_file) -> str:
        """
        Extract raw text from a StoredFile (PDF or DOCX).

        Strategy:
        1. Try pypdf for PDFs (handles text-based PDFs with formatting).
        2. If pypdf returns < 50 chars, fall back to latin-1 byte decoding (catches some scanned PDFs).
        3. For DOCX: parse word/document.xml directly.
        4. Log each stage clearly.
        """
        import logging as _log
        log = _log.getLogger("resume_trust")

        try:
            from apps.documents.services.storage_service import StorageService
            from pathlib import Path as _Path

            path: _Path = StorageService().get_absolute_path(stored_file)
            original_name = (getattr(stored_file, "original_filename", "") or "").lower()

            # ── DOCX extraction ──────────────────────────────────────────────
            if original_name.endswith(".docx"):
                log.info("Text extraction: DOCX mode for %s", getattr(stored_file, "pk", None))
                try:
                    import zipfile
                    from xml.etree import ElementTree
                    parts = []
                    with zipfile.ZipFile(path) as zf:
                        if "word/document.xml" in zf.namelist():
                            xml = zf.read("word/document.xml")
                            root = ElementTree.fromstring(xml)
                            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                            for node in root.findall(".//w:t", ns):
                                if node.text:
                                    parts.append(node.text)
                    text = " ".join(parts)
                    log.info("DOCX extraction: %d chars from %s", len(text), getattr(stored_file, "pk", None))
                    return text
                except Exception as exc:
                    log.warning("DOCX extraction failed for %s: %s", getattr(stored_file, "pk", None), exc)
                    return ""

            # ── PDF extraction ────────────────────────────────────────────────
            log.info("Text extraction: PDF mode for %s", getattr(stored_file, "pk", None))
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                parts = []
                for page in reader.pages[:30]:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        parts.append(page_text)
                pypdf_text = "\n".join(parts)
                log.info(
                    "pypdf extraction: %d chars from %d pages for %s",
                    len(pypdf_text), len(reader.pages), getattr(stored_file, "pk", None),
                )
                if len(pypdf_text.strip()) >= 50:
                    return pypdf_text

                # Fallback for scanned/image-heavy PDFs: raw byte decoding
                log.warning(
                    "pypdf returned < 50 chars for %s — attempting raw byte fallback",
                    getattr(stored_file, "pk", None),
                )
                import re as _re
                raw = path.read_bytes()
                decoded = raw.decode("latin-1", errors="ignore")
                chunks = _re.findall(r"\(([^()\\]{3,120})\)", decoded)
                fallback_text = " ".join(chunks)
                if len(fallback_text.strip()) >= 50:
                    log.info(
                        "Fallback byte extraction: %d chars for %s",
                        len(fallback_text), getattr(stored_file, "pk", None),
                    )
                    return fallback_text

                # If we got something from pypdf even < 50 chars, return it
                # rather than returning empty (better than nothing)
                if pypdf_text.strip():
                    return pypdf_text

                log.warning(
                    "All text extraction methods returned insufficient content for %s (may be scanned/image PDF)",
                    getattr(stored_file, "pk", None),
                )
                return ""

            except ImportError:
                log.warning("pypdf not available — using raw byte fallback for %s", getattr(stored_file, "pk", None))
                import re as _re
                raw = path.read_bytes()
                decoded = raw.decode("latin-1", errors="ignore")
                chunks = _re.findall(r"\(([^()\\]{3,120})\)", decoded)
                return " ".join(chunks)

        except Exception as exc:
            log.error(
                "Text extraction completely failed for %s: %s",
                getattr(stored_file, "pk", None), exc, exc_info=True,
            )
            return ""

