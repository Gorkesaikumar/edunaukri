"""Skill Inflation Detection Rule — detects unrealistic skill breadth or expert-level inflation."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class SkillInflationRule(BaseResumeRule):
    """Detects suspicious skill inflation patterns in resumes.

    Detects:
    - Excessive number of claimed skills (kitchen-sink pattern)
    - Claiming proficiency in contradictory/competing frameworks simultaneously
    - Expert-level claims on technologies released after career start
    - Proficiency in deep specialisations across too many unrelated domains
    """

    RULE_CODE = "SKILL_001"
    RULE_NAME = "Skill Inflation Detection"
    CATEGORY = "Skills"
    DEFAULT_WEIGHT = 15

    # Threshold: more than this many listed skills is suspicious
    SKILL_COUNT_WARNING = 40
    SKILL_COUNT_HIGH = 60

    # Mutually-exclusive deep specialisation domain groups.
    # Having 3+ from BOTH sides is a red flag.
    _COMPETING_DOMAINS: List[Set[str]] = [
        {"ios", "swift", "objective-c", "xcode"},
        {"android", "kotlin", "java android"},
        {"machine learning", "deep learning", "neural network", "transformer"},
        {"front-end", "react", "vue", "angular", "svelte"},
        {"devops", "kubernetes", "terraform", "ansible", "chef", "puppet"},
        {"data engineering", "spark", "kafka", "airflow", "dbt"},
        {"blockchain", "solidity", "web3", "smart contract"},
        {"embedded", "rtos", "fpga", "vhdl", "verilog"},
    ]

    # Technologies released after these years — claiming expertise too soon is a flag
    _RECENT_TECH: Dict[str, int] = {
        "chatgpt api": 2023,
        "gpt-4": 2023,
        "langchain": 2023,
        "llama 2": 2023,
        "gemini": 2023,
        "kubernetes": 2014,
        "react": 2013,
        "flutter": 2018,
        "rust": 2015,
        "next.js": 2016,
    }

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        skills_raw = parsed_data.get("skills") or []
        experience_list = parsed_data.get("experience") or parsed_data.get("work_experience") or []

        # Normalise skills to lowercase strings
        skills: List[str] = []
        for s in skills_raw:
            if isinstance(s, dict):
                skills.append((s.get("name") or s.get("skill") or "").lower())
            else:
                skills.append(str(s).lower())

        # Also extract from raw_text if skills list is thin
        if len(skills) < 5 and raw_text:
            # ponytail: naive keyword presence; upgrade path: NLP entity extractor
            skills_in_text = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{2,}\b", raw_text)
            skills = list(set(skills) | {s.lower() for s in skills_in_text if len(s) > 2})

        if not skills:
            return self._pass(confidence=0.4, metadata={"reason": "no_skills_data"})

        issues: List[str] = []
        evidences: List[str] = []
        skill_set = set(skills)

        # 1. Excessive skill count
        if len(skills) > self.SKILL_COUNT_HIGH:
            issues.append(f"Unrealistic skill count: {len(skills)} skills listed")
            evidences.append(f"{len(skills)} skills")
        elif len(skills) > self.SKILL_COUNT_WARNING:
            issues.append(f"Very high skill count: {len(skills)} skills listed")

        # 2. Deep multi-domain expert inflation
        matched_domains = 0
        for domain_skills in self._COMPETING_DOMAINS:
            overlap = domain_skills & skill_set
            if len(overlap) >= 2:
                matched_domains += 1

        if matched_domains >= 5:
            issues.append(f"Expert-level claims across {matched_domains} unrelated deep specialisation domains")
            evidences.append(f"{matched_domains} specialisation domains matched")

        # 3. Claim of brand-new tech with deep expertise
        career_start_year = self._earliest_start_year(experience_list)
        if career_start_year:
            for tech, release_year in self._RECENT_TECH.items():
                if tech in skill_set or any(tech in s for s in skill_set):
                    years_since_release = 2025 - release_year
                    if years_since_release < 2 and career_start_year < release_year:
                        issues.append(f"Expert claim on '{tech}' released {release_year} but career started {career_start_year}")

        if not issues:
            return self._pass(
                confidence=0.9,
                metadata={"skill_count": len(skills), "domains_matched": matched_domains},
            )

        severity = "HIGH" if len(skills) > self.SKILL_COUNT_HIGH or matched_domains >= 5 else "MEDIUM"
        return self._fail(
            title="Skill Inflation Pattern Detected",
            description=f"{len(issues)} skill inflation signal(s): {'; '.join(issues[:3])}",
            severity=severity,
            penalty=self.DEFAULT_WEIGHT,
            evidence="; ".join(evidences[:3]),
            confidence=0.75,
            recommendation="Validate claimed skills with a technical assessment.",
            metadata={"issues": issues, "skill_count": len(skills)},
        )

    @staticmethod
    def _earliest_start_year(experience_list: List[Dict]) -> int:
        years = []
        pattern = re.compile(r"\b(19|20)\d{2}\b")
        for exp in experience_list:
            raw = str(exp.get("start_date") or exp.get("from") or "")
            m = pattern.search(raw)
            if m:
                years.append(int(m.group()))
        return min(years) if years else None
