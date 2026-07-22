"""Placeholder analyzers returning baseline signals while wiring the complete pipeline."""

from __future__ import annotations

from typing import Any, Dict, List


class ResumePlaceholderAnalyzer:
    """Provides placeholder analysis signals for format, text extraction, and metadata verification."""

    def analyze_format(self, stored_file) -> Dict[str, Any]:
        """Placeholder layout & format analyzer."""
        filename = getattr(stored_file, "original_filename", "") or ""
        is_pdf = filename.lower().endswith(".pdf")
        return {
            "analyzer_name": "FormatAnalyzer",
            "is_valid_format": True,
            "detected_extension": ".pdf" if is_pdf else ".docx",
            "warnings": [],
        }

    def analyze_text_integrity(self, raw_text: str) -> Dict[str, Any]:
        """Placeholder text integrity & font embedding analyzer."""
        char_count = len(raw_text or "")
        return {
            "analyzer_name": "TextIntegrityAnalyzer",
            "character_count": char_count,
            "is_searchable": char_count > 50,
            "warnings": [],
        }

    def analyze_metadata(self, stored_file) -> Dict[str, Any]:
        """Placeholder document author & metadata analyzer."""
        return {
            "analyzer_name": "MetadataAnalyzer",
            "author_verified": True,
            "warnings": [],
        }

    def get_all_placeholder_signals(self, stored_file, raw_text: str = "") -> List[Dict[str, Any]]:
        """Consolidate baseline placeholder analyzer signals."""
        fmt = self.analyze_format(stored_file)
        txt = self.analyze_text_integrity(raw_text)
        meta = self.analyze_metadata(stored_file)
        return [fmt, txt, meta]
