"""Map and validate extracted AI resume data to Job Seeker profile model formats."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from apps.core.validators.common import validate_phone

logger = logging.getLogger(__name__)

url_validator = URLValidator()

INVALID_SENTINEL_VALUES = {
    "",
    "null",
    "none",
    "n/a",
    "na",
    "unknown",
    "not specified",
    "not available",
    "undefined",
    "nil",
    "_",
    "-",
}


def sanitize_text(val: Any) -> str:
    """Return sanitized string or empty string if sentinel/invalid."""
    if val is None:
        return ""
    text = str(val).strip()
    if text.lower() in INVALID_SENTINEL_VALUES:
        return ""
    return text


def sanitize_url(val: Any) -> str:
    """Validate and return URL string or empty string if invalid."""
    text = sanitize_text(val)
    if not text:
        return ""
    if not (text.startswith("http://") or text.startswith("https://")):
        text = "https://" + text
    try:
        url_validator(text)
        return text
    except ValidationError:
        return ""


def sanitize_phone(val: Any) -> str:
    """Validate and format phone number."""
    text = sanitize_text(val)
    if not text:
        return ""
    cleaned = re.sub(r"[^\d+]", "", text)
    if len(cleaned) < 7 or len(cleaned) > 20:
        return ""
    try:
        validate_phone(cleaned)
        return cleaned
    except ValidationError:
        return cleaned if len(cleaned) >= 10 else ""


def sanitize_number(val: Any, min_val: float = 0, max_val: float | None = None) -> float | int | None:
    """Parse numeric values cleanly."""
    if val is None:
        return None
    try:
        num = float(val)
        if num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None
        return int(num) if num.is_integer() else num
    except (ValueError, TypeError):
        return None


def sanitize_date(val: Any) -> date | None:
    """Safely convert date representations (str, date, datetime) to datetime.date or None."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    text = sanitize_text(val)
    if not text:
        return None

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m",
        "%Y/%m",
        "%b %Y",
        "%B %Y",
        "%m/%Y",
        "%Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


@dataclass
class MappedProfileData:
    profile_fields: dict[str, Any] = field(default_factory=dict)
    skills: list[str] = field(default_factory=list)
    education: list[dict[str, Any]] = field(default_factory=list)
    experiences: list[dict[str, Any]] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    certifications: list[dict[str, Any]] = field(default_factory=list)


class ResumeProfileMapper:
    """Mapper converting raw extracted AI resume JSON to validated profile DTO."""

    def map_parsed_data(self, parsed: dict[str, Any]) -> MappedProfileData:
        if not parsed or not isinstance(parsed, dict):
            return MappedProfileData()

        mapped = MappedProfileData()

        # 1. Profile primitive fields
        fields: dict[str, Any] = {}

        phone = sanitize_phone(parsed.get("phone"))
        if phone:
            fields["phone"] = phone

        summary = sanitize_text(parsed.get("summary") or parsed.get("about"))
        if summary:
            fields["summary"] = summary

        headline = sanitize_text(parsed.get("headline") or parsed.get("title"))
        if headline:
            fields["headline"] = headline[:300]

        city = sanitize_text(parsed.get("city"))
        if city:
            fields["city"] = city[:100]

        state = sanitize_text(parsed.get("state"))
        if state:
            fields["state"] = state[:100]

        country = sanitize_text(parsed.get("country"))
        if country:
            fields["country"] = country[:100]

        current_location = sanitize_text(parsed.get("current_location") or parsed.get("location"))
        if current_location:
            fields["current_location"] = current_location[:200]

        preferred_location = sanitize_text(parsed.get("preferred_location"))
        if preferred_location:
            fields["preferred_location"] = preferred_location[:200]

        current_company = sanitize_text(parsed.get("current_company") or parsed.get("company"))
        if current_company:
            fields["current_company"] = current_company[:200]

        exp_years = sanitize_number(parsed.get("experience_years") or parsed.get("total_experience_years"), min_val=0, max_val=60)
        if exp_years is not None:
            fields["experience_years"] = int(exp_years)

        # Social Links
        social = parsed.get("social_links") or {}
        if isinstance(social, dict):
            linkedin = sanitize_url(social.get("linkedin") or parsed.get("linkedin_url") or parsed.get("linkedin"))
            if linkedin:
                fields["linkedin_url"] = linkedin
            github = sanitize_url(social.get("github") or parsed.get("github_url") or parsed.get("github"))
            if github:
                fields["github_url"] = github
            portfolio = sanitize_url(social.get("portfolio") or parsed.get("portfolio_url") or parsed.get("portfolio"))
            if portfolio:
                fields["portfolio_url"] = portfolio
            website = sanitize_url(social.get("website") or parsed.get("personal_website") or parsed.get("website"))
            if website:
                fields["personal_website"] = website
        else:
            for key, field_name in [("linkedin", "linkedin_url"), ("github", "github_url"), ("portfolio", "portfolio_url"), ("website", "personal_website")]:
                url_val = sanitize_url(parsed.get(key) or parsed.get(field_name))
                if url_val:
                    fields[field_name] = url_val

        # Lists
        languages_raw = parsed.get("languages") or []
        if isinstance(languages_raw, list):
            clean_langs = [sanitize_text(l) for l in languages_raw if sanitize_text(l)]
            if clean_langs:
                fields["languages"] = clean_langs

        roles_raw = parsed.get("preferred_roles") or parsed.get("roles") or []
        if isinstance(roles_raw, list):
            clean_roles = [sanitize_text(r) for r in roles_raw if sanitize_text(r)]
            if clean_roles:
                fields["preferred_roles"] = clean_roles

        mapped.profile_fields = fields

        # 2. Skills
        raw_skills = parsed.get("skills") or []
        if isinstance(raw_skills, list):
            clean_skills = []
            for s in raw_skills:
                item = sanitize_text(s)
                if item and item not in clean_skills:
                    clean_skills.append(item[:100])
            mapped.skills = clean_skills

        # 3. Experiences
        raw_exp = parsed.get("experience") or parsed.get("experiences") or []
        if isinstance(raw_exp, list):
            for entry in raw_exp:
                exp_dict = self._map_experience_entry(entry)
                if exp_dict:
                    mapped.experiences.append(exp_dict)

        # 4. Education
        raw_edu = parsed.get("education") or []
        if isinstance(raw_edu, list):
            for entry in raw_edu:
                edu_dict = self._map_education_entry(entry)
                if edu_dict:
                    mapped.education.append(edu_dict)

        # 5. Projects
        raw_proj = parsed.get("projects") or []
        if isinstance(raw_proj, list):
            for entry in raw_proj:
                proj_dict = self._map_project_entry(entry)
                if proj_dict:
                    mapped.projects.append(proj_dict)

        # 6. Certifications
        raw_cert = parsed.get("certifications") or parsed.get("certificates") or []
        if isinstance(raw_cert, list):
            for entry in raw_cert:
                cert_dict = self._map_certification_entry(entry)
                if cert_dict:
                    mapped.certifications.append(cert_dict)

        return mapped

    def _map_experience_entry(self, entry: Any) -> dict[str, Any] | None:
        if isinstance(entry, str):
            clean_str = sanitize_text(entry)
            if not clean_str:
                return None
            parts = clean_str.split("-", 1)
            title = parts[0].strip()[:200]
            company = parts[1].strip()[:200] if len(parts) > 1 else "Experience Entry"
            return {"company_name": company, "title": title, "description": clean_str}
        if not isinstance(entry, dict):
            return None

        company = sanitize_text(entry.get("company_name") or entry.get("company") or entry.get("organization"))
        title = sanitize_text(entry.get("title") or entry.get("role") or entry.get("designation"))

        if not company and not title:
            return None

        return {
            "company_name": (company or title or "Company")[:200],
            "title": (title or company or "Role")[:200],
            "location": sanitize_text(entry.get("location"))[:200],
            "start_date": sanitize_date(entry.get("start_date")),
            "end_date": sanitize_date(entry.get("end_date")),
            "is_current": bool(entry.get("is_current") or entry.get("current")),
            "description": sanitize_text(entry.get("description") or entry.get("summary") or entry.get("details")),
        }

    def _map_education_entry(self, entry: Any) -> dict[str, Any] | None:
        if isinstance(entry, str):
            clean_str = sanitize_text(entry)
            if not clean_str:
                return None
            return {
                "institution": clean_str[:300],
                "degree": clean_str[:200],
            }
        if not isinstance(entry, dict):
            return None

        inst = sanitize_text(entry.get("institution") or entry.get("college") or entry.get("university") or entry.get("school"))
        degree = sanitize_text(entry.get("degree") or entry.get("qualification") or entry.get("course"))
        field_of_study = sanitize_text(entry.get("field_of_study") or entry.get("stream") or entry.get("major") or entry.get("branch"))

        if not inst and not degree:
            return None

        passing_year = sanitize_number(entry.get("passing_year") or entry.get("year"), min_val=1950, max_val=2100)
        start_year = sanitize_number(entry.get("start_year"), min_val=1950, max_val=2100)
        end_year = sanitize_number(entry.get("end_year"), min_val=1950, max_val=2100)

        cgpa = sanitize_number(entry.get("cgpa"), min_val=0, max_val=10)
        percentage = sanitize_number(entry.get("percentage"), min_val=0, max_val=100)

        return {
            "institution": (inst or degree or "Institution")[:300],
            "degree": (degree or inst or "Degree")[:200],
            "field_of_study": field_of_study[:200],
            "passing_year": int(passing_year) if passing_year else None,
            "start_year": int(start_year) if start_year else None,
            "end_year": int(end_year) if end_year else None,
            "cgpa": cgpa,
            "percentage": percentage,
        }

    def _map_project_entry(self, entry: Any) -> dict[str, Any] | None:
        if isinstance(entry, str):
            clean_str = sanitize_text(entry)
            if not clean_str:
                return None
            return {"title": clean_str[:200], "description": clean_str}
        if not isinstance(entry, dict):
            return None

        title = sanitize_text(entry.get("title") or entry.get("name"))
        if not title:
            return None

        tech_raw = entry.get("technologies") or entry.get("tech_stack") or []
        tech_list = []
        if isinstance(tech_raw, list):
            tech_list = [sanitize_text(t) for t in tech_raw if sanitize_text(t)]
        elif isinstance(tech_raw, str):
            tech_list = [t.strip() for t in tech_raw.split(",") if t.strip()]

        return {
            "title": title[:200],
            "description": sanitize_text(entry.get("description") or entry.get("details")),
            "technologies": tech_list,
            "project_url": sanitize_url(entry.get("project_url") or entry.get("url")),
            "github_url": sanitize_url(entry.get("github_url") or entry.get("github")),
        }

    def _map_certification_entry(self, entry: Any) -> dict[str, Any] | None:
        if isinstance(entry, str):
            clean_str = sanitize_text(entry)
            if not clean_str:
                return None
            return {"name": clean_str[:300]}
        if not isinstance(entry, dict):
            return None

        name = sanitize_text(entry.get("name") or entry.get("title") or entry.get("certificate"))
        if not name:
            return None

        org = sanitize_text(entry.get("issuing_organization") or entry.get("issuer") or entry.get("organization"))

        return {
            "name": name[:300],
            "issuing_organization": org[:300],
            "issue_date": sanitize_date(entry.get("issue_date") or entry.get("date")),
            "expiry_date": sanitize_date(entry.get("expiry_date") or entry.get("expiration_date")),
            "credential_id": sanitize_text(entry.get("credential_id") or entry.get("id"))[:200],
            "credential_url": sanitize_url(entry.get("credential_url") or entry.get("url")),
        }
