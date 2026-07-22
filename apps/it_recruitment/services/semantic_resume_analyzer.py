"""
Semantic AI-Assisted Resume Analyzer.
Extracts sections, boundaries, and candidate info without relying on strict headers.
"""

import logging
import re
from typing import Dict, List, Tuple

from apps.core.services.base import BaseService

logger = logging.getLogger(__name__)

class SemanticResumeAnalyzer(BaseService):
    """
    Intelligently infers resume sections by contextual boundaries rather than fixed layout.
    """

    # Semantic mappings of arbitrary headers into standardized internal blocks
    SECTION_MAPPING = {
        "summary": [
            "professional summary", "career objective", "about me", "profile", 
            "personal statement", "executive summary", "summary of qualifications"
        ],
        "experience": [
            "work experience", "professional experience", "employment history", 
            "career history", "experience", "employment", "work history"
        ],
        "projects": [
            "projects", "academic projects", "personal projects", "research", 
            "key projects", "notable projects"
        ],
        "skills": [
            "skills", "technical skills", "core skills", "competencies", 
            "technologies", "expertise", "core competencies", "technical expertise"
        ],
        "education": [
            "education", "academic qualification", "qualifications", "academic background", 
            "academics", "educational background"
        ],
        "certifications": [
            "training", "certifications", "certificates", "licenses", "courses"
        ]
    }

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s\-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s\-]?\d{3,4}[\s\-]?\d{3,4}")

    def analyze(self, raw_text: str, profile_name: str = "") -> dict:
        """
        Runs the semantic analysis over raw OCR or native text.
        """
        clean_text = self._clean_text(raw_text)
        lines = [ln.strip() for ln in clean_text.split("\n") if ln.strip()]
        
        # 1. Extract Candidate Info
        emails = self.EMAIL_RE.findall(clean_text)
        phones = self.PHONE_RE.findall(clean_text)
        
        name = profile_name
        if not name and lines:
            # Assume first non-empty line without email/phone is name
            for line in lines[:5]:
                if "@" not in line and not self.PHONE_RE.search(line) and len(line.split()) <= 4:
                    name = line
                    break

        # 2. Extract Sections Boundaries
        sections = self._infer_sections(lines)
        
        # 3. Extract Keywords/Skills
        raw_skills = self._extract_skills(sections.get("skills", []), clean_text)
        
        return {
            "name": name,
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "skills": raw_skills,
            "keywords": raw_skills, # Fallback 
            "education": sections.get("education", [])[:10],
            "experience": sections.get("experience", [])[:10],
            "projects": sections.get("projects", [])[:10],
            "certifications": sections.get("certifications", [])[:10],
            "summary": sections.get("summary", [])[:10],
            "text_length": len(clean_text)
        }

    def _clean_text(self, text: str) -> str:
        # Standardize spaces and odd characters from OCR
        text = re.sub(r"[^\x00-\x7F\t\n]+", " ", text)
        # Convert tabs to newlines for column layouts
        text = text.replace("\t", "\n")
        # Convert multiple spaces (4+) to newline, as they often denote columns
        text = re.sub(r" {4,}", "\n", text)
        text = re.sub(r" +", " ", text)
        return text

    def _infer_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        """
        Scans lines sequentially and groups them under the detected semantic header.
        """
        sections: Dict[str, List[str]] = {}
        current_section = None
        
        for line in lines:
            line_lower = line.lower().strip()
            # Clean up OCR bullets or symbols at start of line
            clean_header = re.sub(r"^[^a-z0-9]+", "", line_lower).strip()
            
            # Is this line a header? (Short length, matches semantic dict)
            detected_header = None
            if len(clean_header) > 3 and len(clean_header) < 40:
                for sec_key, variants in self.SECTION_MAPPING.items():
                    if any(v == clean_header or clean_header.startswith(v) for v in variants):
                        detected_header = sec_key
                        break
            
            if detected_header:
                current_section = detected_header
                if current_section not in sections:
                    sections[current_section] = []
                continue
            
            if current_section:
                # Add line to current section
                if len(line) > 3:
                    sections[current_section].append(line)
                    
        return sections

    def _extract_skills(self, skill_lines: List[str], full_text: str) -> List[str]:
        """
        Merge skills explicitly stated in 'Skills' section + infer from full text.
        """
        # A basic heuristic: if skills section exists, split by commas, dashes, bullets
        extracted = []
        for line in skill_lines:
            tokens = [t.strip().title() for t in re.split(r"[,|•\-]", line) if len(t.strip()) > 1]
            extracted.extend(tokens)
            
        # Fallback to general tech scanning if needed
        if not extracted:
            common_tech = ["Python", "Java", "React", "AWS", "SQL", "Docker", "Node.js"]
            for tech in common_tech:
                if tech.lower() in full_text.lower():
                    extracted.append(tech)
                    
        return list(set(extracted))[:50]
