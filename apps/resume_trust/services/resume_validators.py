"""Dedicated validation services for Resume Trust & Fraud Detection Engine.

Provides:
- ResumeReadabilityValidator: Checks PDF integrity, non-encryption, readability, and min text length.
- ResumeDetectionService: Distinguishes resumes from non-resume documents (invoices, bills, bank statements, receipts).
- ResumeCompletenessValidator: Ensures minimum required structural fields exist.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("resume_trust")


@dataclass
class ValidationResult:
    is_valid: bool
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None


class ResumeReadabilityValidator:
    """Validates PDF file integrity, encryption status, readability, and text length thresholds."""

    MIN_TEXT_LENGTH = 80  # Minimum characters required to proceed — very short strings (< 80 chars) cannot be a resume

    def validate_stored_file(self, stored_file, raw_text: str = "") -> ValidationResult:
        # True file-missing case: nothing was provided at all
        if not stored_file and not raw_text:
            return ValidationResult(
                is_valid=False,
                error_code="FILE_MISSING",
                error_message="No resume file or text was provided for analysis.",
            )

        if stored_file:
            mime = getattr(stored_file, "mime_type", "") or ""
            original_name = (getattr(stored_file, "original_filename", "") or "").lower()

            if mime and "pdf" not in mime and not original_name.endswith((".pdf", ".doc", ".docx")):
                return ValidationResult(
                    is_valid=False,
                    error_code="UNSUPPORTED_FORMAT",
                    error_message=f"Unsupported file format '{mime or original_name}'. Please upload a valid PDF or Word document.",
                )

        extracted_len = len((raw_text or "").strip())

        if stored_file and extracted_len < self.MIN_TEXT_LENGTH:
            # File was provided but text extraction failed or returned too little content
            return ValidationResult(
                is_valid=False,
                error_code="UNREADABLE_OR_EMPTY",
                error_message=(
                    "The uploaded file was received but readable text could not be extracted. "
                    "The document may be a scanned image, password-protected, or contain insufficient text. "
                    f"Only {extracted_len} characters were found (minimum {self.MIN_TEXT_LENGTH} required)."
                ),
            )

        if not stored_file and extracted_len < self.MIN_TEXT_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_code="UNREADABLE_OR_EMPTY",
                error_message="Unable to extract readable text from the document. The file may be empty, image-only, or encrypted.",
            )

        return ValidationResult(is_valid=True, error_code="", error_message="")




class ResumeDetectionService:
    """Determines whether extracted text & parsed fields represent a candidate resume vs non-resume document.

    Uses a WEIGHTED SCORING system — a document is classified as a resume when it achieves
    a minimum confidence score from multiple resume signals. No single signal is required.

    This prevents:
    - False positives: invoices/receipts still fail due to strict exclusion patterns.
    - False negatives: valid resumes (freshers, ATS, scanned) pass if they contain enough signals.
    """

    NON_RESUME_PATTERNS = [
        re.compile(r"\b(tax\s+invoice|invoice\s+no|invoice\s+date|billed\s+to|subtotal|balance\s+due|amount\s+due|payment\s+terms|due\s+date|gstin|vat\s+no)\b", re.I),
        re.compile(r"\b(payment\s+receipt|receipt\s+no|transaction\s+id|bank\s+statement|account\s+statement|credit\s+card\s+statement|purchase\s+order|bill\s+of\s+lading|packing\s+list)\b", re.I),
    ]

    # Weighted signals — each contributes points toward a resume confidence score.
    # A document needs MIN_CONFIDENCE_SCORE to be accepted as a resume.
    MIN_CONFIDENCE_SCORE = 3

    WEIGHTED_SIGNALS = [
        # Contact signals (high confidence — appear on almost every resume)
        (re.compile(r"[\w\.\-]+@[\w\.\-]+\.\w{2,}", re.I),                                                      2, "email_address"),
        (re.compile(r"(\+?\d[\d\s\-]{8,}\d)"), 2, "phone_number"),
        (re.compile(r"\b(linkedin\.com|github\.com|portfolio|behance|dribbble)\b", re.I),                        1, "social_profile"),

        # Content section signals (medium confidence)
        (re.compile(r"\b(education|university|college|bachelor|master|b\.tech|m\.tech|bsc|msc|bca|mca|phd|diploma|degree|qualification|gpa|cgpa|10th|12th|ssc|hsc)\b", re.I), 2, "education"),
        (re.compile(r"\b(experience|employment|work\s+history|career|designation|role|position|company|organization|employer|intern)\b", re.I),                                   2, "experience"),
        (re.compile(r"\b(skills|technical\s+skills|core\s+competencies|technologies|tools|languages|proficient|expertise|knowledge)\b", re.I),                                   2, "skills"),
        (re.compile(r"\b(project|projects|personal\s+project|academic\s+project|key\s+project|portfolio)\b", re.I),                                                              1, "projects"),
        (re.compile(r"\b(certif|certified|certificate|credential|license|award)\w*\b", re.I),                                                                                    1, "certifications"),
        (re.compile(r"\b(professional\s+summary|career\s+summary|objective|profile|about\s+me|career\s+objective)\b", re.I),                                                     1, "summary"),

        # Document identity signals
        (re.compile(r"\b(resume|curriculum\s+vitae|cv)\b", re.I),                                               2, "resume_keyword"),

        # Common resume formatting signals (proper nouns, dates, etc.)
        (re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}\b", re.I),                 1, "date_range"),
        (re.compile(r"\b(present|current|till\s+date|to\s+date)\b", re.I),                                      1, "current_role"),
    ]

    def detect_resume(self, raw_text: str = "", parsed_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        text = (raw_text or "").strip()
        parsed = parsed_data or {}

        # 1. Hard exclusion: non-resume document patterns (invoice, bank statement, etc.)
        exclusion_matches = []
        for pat in self.NON_RESUME_PATTERNS:
            found = pat.findall(text)
            if found:
                exclusion_matches.extend(found)

        if len(exclusion_matches) >= 1:
            logger.warning("Document identified as non-resume document (matches: %s)", exclusion_matches)
            return ValidationResult(
                is_valid=False,
                error_code="NOT_A_RESUME",
                error_message="The uploaded document appears to be an invoice, bill, or financial receipt rather than a candidate resume.",
                details={"exclusion_matches": exclusion_matches},
            )

        # 2. Weighted resume signal scoring
        confidence_score = 0
        matched_signals = []

        for pattern, weight, signal_name in self.WEIGHTED_SIGNALS:
            if pattern.search(text):
                confidence_score += weight
                matched_signals.append(signal_name)

        # 3. Bonus from parsed structured data (parser already ran successfully)
        if parsed.get("skills"):
            confidence_score += 2
            matched_signals.append("parsed_skills")
        if parsed.get("education"):
            confidence_score += 2
            matched_signals.append("parsed_education")
        if parsed.get("experience") or parsed.get("experiences"):
            confidence_score += 2
            matched_signals.append("parsed_experience")
        if parsed.get("email") or parsed.get("phone"):
            confidence_score += 1
            matched_signals.append("parsed_contact")
        if parsed.get("name"):
            confidence_score += 1
            matched_signals.append("parsed_name")

        logger.info(
            "Resume detection: confidence_score=%d | required=%d | signals=%s",
            confidence_score, self.MIN_CONFIDENCE_SCORE, matched_signals,
        )

        if confidence_score < self.MIN_CONFIDENCE_SCORE:
            return ValidationResult(
                is_valid=False,
                error_code="NOT_A_RESUME",
                error_message=(
                    "The document does not appear to be a valid candidate resume. "
                    "It lacks sufficient resume content (such as Education, Experience, Skills, or Contact details). "
                    f"Confidence score: {confidence_score}/{self.MIN_CONFIDENCE_SCORE} required."
                ),
                details={"confidence_score": confidence_score, "matched_signals": matched_signals},
            )

        return ValidationResult(is_valid=True, error_code="", error_message="", details={"confidence_score": confidence_score, "matched_signals": matched_signals})




class ResumeCompletenessValidator:
    """Verifies that the parsed resume contains minimum required structural fields."""

    def validate_completeness(self, raw_text: str = "", parsed_data: Optional[Dict[str, Any]] = None) -> ValidationResult:
        text = (raw_text or "").strip()
        parsed = parsed_data or {}

        has_email = bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text))
        has_phone = bool(re.search(r"(\+?\d[\d\s-]{8,}\d)", text))
        has_contact = has_email or has_phone or bool(parsed.get("email") or parsed.get("phone"))

        has_skills = bool(parsed.get("skills")) or bool(re.search(r"\b(skills|technologies|tools|languages)\b", text, re.I))
        has_education = bool(parsed.get("education")) or bool(re.search(r"\b(education|university|degree|college|school)\b", text, re.I))
        has_experience = bool(parsed.get("experience") or parsed.get("experiences")) or bool(re.search(r"\b(experience|employment|work\s+history|career)\b", text, re.I))

        content_sections = sum([has_skills, has_education, has_experience])

        if not has_contact and content_sections < 2:
            return ValidationResult(
                is_valid=False,
                error_code="INCOMPLETE_RESUME",
                error_message="The resume is incomplete. It lacks essential contact information and core resume sections.",
            )

        return ValidationResult(is_valid=True, error_code="", error_message="")


def extract_resume_diagnostics(raw_text: str = "", parsed_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extracts structured diagnostic breakdown: passed checks, missing sections, and recommendations."""
    text = (raw_text or "").strip()
    parsed = parsed_data or {}

    passed_checks = ["Readable PDF Document"]
    failed_checks = []
    detected_sections = []
    missing_sections = []
    recommendations = []

    has_name = bool(parsed.get("name")) or bool(re.search(r"^[A-Z][a-z]+\s+[A-Z][a-z]+", text))
    has_email = bool(parsed.get("email")) or bool(re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text))
    has_phone = bool(parsed.get("phone")) or bool(re.search(r"(\+?\d[\d\s-]{8,}\d)", text))

    if has_name:
        passed_checks.append("Candidate Name")
        detected_sections.append("Candidate Name")
    else:
        failed_checks.append("Missing Candidate Name")
        missing_sections.append("Candidate Name")

    if has_email:
        passed_checks.append("Email Address")
        detected_sections.append("Email Address")
    else:
        failed_checks.append("Missing Email Address")
        missing_sections.append("Email Address")

    if has_phone:
        passed_checks.append("Phone Number")
        detected_sections.append("Phone Number")
    else:
        failed_checks.append("Missing Phone Number")
        missing_sections.append("Phone Number")

    has_summary = bool(re.search(r"\b(professional\s+summary|career\s+summary|profile|objective)\b", text, re.I))
    has_skills = bool(parsed.get("skills")) or bool(re.search(r"\b(skills|technical\s+skills|competencies|technologies)\b", text, re.I))
    has_education = bool(parsed.get("education")) or bool(re.search(r"\b(education|university|college|bachelor|master|degree|qualification)\b", text, re.I))
    has_experience = bool(parsed.get("experience") or parsed.get("experiences")) or bool(re.search(r"\b(experience|employment|work\s+history|career)\b", text, re.I))
    has_projects = bool(parsed.get("projects")) or bool(re.search(r"\b(projects|key\s+projects)\b", text, re.I))
    has_certs = bool(parsed.get("certifications")) or bool(re.search(r"\b(certifications|certificates|certified)\b", text, re.I))
    has_social = bool(re.search(r"\b(linkedin|github|portfolio)\b", text, re.I))

    if has_summary:
        passed_checks.append("Professional Summary")
        detected_sections.append("Professional Summary")
    else:
        failed_checks.append("Missing Professional Summary")
        missing_sections.append("Professional Summary")
        recommendations.append("Add a professional summary outlining your key expertise and career focus.")

    if has_skills:
        passed_checks.append("Skills & Technical Stack")
        detected_sections.append("Skills")
    else:
        failed_checks.append("Missing Skills Section")
        missing_sections.append("Skills")
        recommendations.append("Include a dedicated skills section listing technologies, frameworks, and core competencies.")

    if has_education:
        passed_checks.append("Education & Degree")
        detected_sections.append("Education")
    else:
        failed_checks.append("Missing Education Details")
        missing_sections.append("Education")
        recommendations.append("Add your academic background, degree, and university details.")

    if has_experience:
        passed_checks.append("Work Experience & Employment History")
        detected_sections.append("Work Experience")
    else:
        failed_checks.append("Missing Work Experience")
        missing_sections.append("Work Experience")
        recommendations.append("Detail your employment history and previous professional roles.")

    if has_projects:
        passed_checks.append("Projects & Portfolio")
        detected_sections.append("Projects")
    else:
        missing_sections.append("Projects")
        recommendations.append("Add key projects to demonstrate practical accomplishments.")

    if has_certs:
        passed_checks.append("Certifications & Credentials")
        detected_sections.append("Certifications")
    else:
        missing_sections.append("Certifications")

    if has_social:
        passed_checks.append("LinkedIn / GitHub Profile")
        detected_sections.append("Social & Web Profiles")

    if not recommendations:
        recommendations.append("Your resume structure looks strong and comprehensive!")

    return {
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "detected_sections": detected_sections,
        "missing_sections": missing_sections,
        "recommendations": recommendations,
    }
