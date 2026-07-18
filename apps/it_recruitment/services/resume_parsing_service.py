"""Extract structured data from uploaded resume files (PDF / DOCX)."""

from __future__ import annotations

import logging
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from django.utils import timezone

from apps.core.services.base import BaseService
from apps.documents.models import StoredFile
from apps.documents.services.storage_service import StorageService

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s\-]?\d{3,4}[\s\-]?\d{3,4}"
)
SKILL_HINTS = (
    "python",
    "django",
    "javascript",
    "react",
    "java",
    "sql",
    "aws",
    "docker",
    "kubernetes",
    "typescript",
    "node",
    "html",
    "css",
    "postgresql",
    "mongodb",
    "redis",
    "celery",
    "rest",
    "api",
    "git",
    "linux",
    "agile",
    "scrum",
    "machine learning",
    "data analysis",
    "excel",
    "communication",
    "leadership",
)


class ResumeParsingService(BaseService):
    """Parse resume files and persist structured extraction on StoredFile.parsed_data."""

    PARSED_KEY = "extracted"

    def parse_and_store(self, stored: StoredFile, *, profile=None) -> dict:
        text = self._extract_text(stored)
        parsed = self._analyze_text(text, profile=profile)
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
        ext = Path(stored.original_filename or "").suffix.lower()
        try:
            if ext == ".pdf":
                return self._extract_pdf_text(path)
            if ext == ".docx":
                return self._extract_docx_text(path)
        except Exception as exc:
            logger.warning("Resume text extraction failed for %s: %s", stored.pk, exc)
        return ""

    @staticmethod
    def _extract_pdf_text(path: Path) -> str:
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages[:20]:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except ImportError:
            raw = path.read_bytes()
            decoded = raw.decode("latin-1", errors="ignore")
            chunks = re.findall(r"\(([^()\\]{3,120})\)", decoded)
            return " ".join(chunks)

    @staticmethod
    def _extract_docx_text(path: Path) -> str:
        parts: list[str] = []
        with zipfile.ZipFile(path) as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            xml = zf.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            for node in root.findall(".//w:t", ns):
                if node.text:
                    parts.append(node.text)
        return " ".join(parts)

    def _analyze_text(self, text: str, *, profile=None) -> dict:
        clean = re.sub(r"\s+", " ", text).strip()
        lower = clean.lower()
        emails = EMAIL_RE.findall(clean)
        phones = PHONE_RE.findall(clean)
        skills = sorted({hint.title() for hint in SKILL_HINTS if hint in lower})
        keywords = sorted(
            {
                token
                for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{2,}", lower)
                if len(token) > 3
            }
        )[:80]

        name = ""
        if profile and profile.full_name:
            name = profile.full_name
        elif clean:
            first_line = clean.split("\n")[0][:120]
            if first_line and "@" not in first_line:
                name = first_line.strip()

        education = self._extract_section_lines(
            clean, ("education", "qualification", "academic")
        )
        experience = self._extract_section_lines(
            clean, ("experience", "employment", "work history")
        )
        projects = self._extract_section_lines(clean, ("projects", "project"))
        certifications = self._extract_section_lines(
            clean, ("certification", "certificate", "licenses")
        )

        return {
            "name": name,
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "skills": skills,
            "keywords": keywords,
            "education": education[:5],
            "experience": experience[:5],
            "projects": projects[:5],
            "certifications": certifications[:5],
            "technologies": [
                s for s in skills if any(c.isupper() for c in s) or "+" in s
            ][:15],
            "parsed_at": timezone.now().isoformat(),
            "text_length": len(clean),
        }

    @staticmethod
    def _extract_section_lines(text: str, headers: tuple[str, ...]) -> list[str]:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        results: list[str] = []
        capture = False
        for line in lines:
            lower = line.lower()
            if any(h in lower for h in headers) and len(line) < 80:
                capture = True
                continue
            if capture:
                if len(line) < 3:
                    continue
                if line.isupper() and len(line) < 40:
                    break
                results.append(line[:200])
                if len(results) >= 5:
                    break
        return results

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
