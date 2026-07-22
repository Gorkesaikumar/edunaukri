"""Orchestrates Native Text Extraction and OCR for diverse resume formats."""

import logging
from pathlib import Path

from django.utils import timezone

from apps.core.services.base import BaseService
from apps.documents.models import StoredFile
from apps.documents.services.storage_service import StorageService
from apps.it_recruitment.services.resume_ocr_service import ResumeOCRService
from apps.it_recruitment.services.semantic_resume_analyzer import SemanticResumeAnalyzer

logger = logging.getLogger(__name__)

class UniversalResumeParserService(BaseService):
    """
    Production-grade Universal Parser.
    Automatically routes to native extraction or OCR, then applies Semantic AI understanding.
    """

    PARSED_KEY = "extracted"

    def parse_and_store(self, stored: StoredFile, *, profile=None) -> dict:
        """
        Extract text via Native or OCR, parse semantically, and store results.
        """
        from apps.resume_trust.services.resume_progress_tracker import ResumeProgressTracker
        
        ResumeProgressTracker.advance(stored.pk, "PDF_VALIDATED")
        raw_text = self._extract_text(stored)
        ResumeProgressTracker.advance(stored.pk, "TEXT_EXTRACTED")
        
        # Determine name fallback
        profile_name = ""
        if profile and getattr(profile, "full_name", None):
            profile_name = profile.full_name
            
        analyzer = SemanticResumeAnalyzer()
        parsed = analyzer.analyze(raw_text, profile_name=profile_name)
        ResumeProgressTracker.advance(stored.pk, "RESUME_DETECTED")
        
        # In a more granular implementation we could hook into the analyzer directly, 
        # but for simplicity we simulate the analyzer's rapid stages here:
        import time
        ResumeProgressTracker.advance(stored.pk, "AI_ANALYSIS_STARTED")
        time.sleep(0.5)
        if parsed.get("skills"):
            ResumeProgressTracker.advance(stored.pk, "SKILLS_ANALYZED")
            time.sleep(0.5)
        if parsed.get("education"):
            ResumeProgressTracker.advance(stored.pk, "EDUCATION_ANALYZED")
            time.sleep(0.5)
        if parsed.get("experience"):
            ResumeProgressTracker.advance(stored.pk, "EXPERIENCE_ANALYZED")
        
        # Persist extracted payload
        payload = dict(stored.parsed_data or {})
        payload[self.PARSED_KEY] = parsed
        payload["version"] = int(payload.get("version") or 0) + 1
        stored.parsed_data = payload
        stored.parsed_at = timezone.now()
        stored.save(update_fields=["parsed_data", "parsed_at", "updated_at"])
        
        return parsed

    def get_extracted(self, stored: StoredFile | None) -> dict:
        if not stored:
            return {}
        return (stored.parsed_data or {}).get(self.PARSED_KEY) or {}

    def _extract_text(self, stored: StoredFile) -> str:
        path = StorageService().get_absolute_path(stored)
        if not Path(path).exists():
            logger.error(f"StoredFile {stored.pk} path {path} does not exist.")
            return ""
            
        ext = Path(stored.original_filename or "").suffix.lower()
        
        # 1. Image formats immediately route to OCR
        if ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff"):
            logger.info(f"Image format detected ({ext}). Routing to OCR.")
            return ResumeOCRService().extract_text(Path(path))
            
        # 2. Text formats try Native first
        text = ""
        if ext == ".pdf":
            text = self._extract_pdf_native(Path(path))
        elif ext == ".docx":
            text = self._extract_docx_native(Path(path))
            
        # 3. Fallback to OCR if native text is insufficient (scanned PDFs)
        if len(text.strip()) < 80:
            logger.info(f"Native extraction yielded < 80 chars. Routing {ext} to OCR.")
            try:
                ocr_text = ResumeOCRService().extract_text(Path(path))
                if ocr_text.strip():
                    return ocr_text
            except Exception as e:
                logger.error(f"OCR fallback failed: {e}")
                
        return text

    @staticmethod
    def _extract_pdf_native(path: Path) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            parts = [page.extract_text() or "" for page in reader.pages[:20]]
            text = "\n".join(parts)
            if len(text.strip()) > 80:
                return text
                
            # 👱‍♀️ ponytail: Fallback for Canva/Scanned PDFs without relying on heavy OCR dependencies.
            # Canva and some generators encode text strings directly in PDF drawing operators inside parentheses: (Text)
            import re
            decoded = path.read_bytes().decode("latin-1", errors="ignore")
            chunks = re.findall(r"\(([^()\\]{3,120})\)", decoded)
            return " ".join(chunks)
            
        except Exception as e:
            logger.warning(f"Native PDF extraction failed: {e}")
            return ""

    @staticmethod
    def _extract_docx_native(path: Path) -> str:
        import zipfile
        from xml.etree import ElementTree
        try:
            with zipfile.ZipFile(path) as zf:
                if "word/document.xml" not in zf.namelist():
                    return ""
                xml = zf.read("word/document.xml")
                root = ElementTree.fromstring(xml)
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                paragraphs = []
                for p in root.findall(".//w:p", ns):
                    parts = []
                    for child in p.iter():
                        if child.tag.endswith('}t') and child.text:
                            parts.append(child.text)
                        elif child.tag.endswith('}br'):
                            parts.append("\n")
                        elif child.tag.endswith('}tab'):
                            parts.append("\t")
                    if parts:
                        paragraphs.append("".join(parts))
            return "\n".join(paragraphs)
        except Exception as e:
            logger.warning(f"Native DOCX extraction failed: {e}")
            return ""

    @staticmethod
    def suggest_profile_autofill(parsed: dict, profile) -> list[dict]:
        """Fields empty on profile that parsed resume can fill."""
        suggestions: list[dict] = []
        if parsed.get("phone") and not (profile.phone or "").strip():
            suggestions.append(
                {"field": "phone", "label": "Phone Number", "value": parsed["phone"]}
            )
        if parsed.get("email") and not (profile.user.email or "").strip():
            suggestions.append(
                {"field": "email", "label": "Email", "value": parsed["email"]}
            )
        if (
            parsed.get("skills")
            and not profile.skills.filter(is_deleted=False).exists()
        ):
            suggestions.append(
                {
                    "field": "skills",
                    "label": "Skills",
                    "value": ", ".join(parsed["skills"][:8]),
                }
            )
        return suggestions
