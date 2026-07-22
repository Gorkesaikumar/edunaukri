"""Duplicate Keyword Detection Rule — detects ATS-stuffing and keyword repetition patterns."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from apps.resume_trust.services.rules.base_rule import BaseResumeRule, RuleResult


class DuplicateKeywordRule(BaseResumeRule):
    """Detects keyword stuffing — a common ATS-gaming tactic.

    Detects:
    - High-frequency repetition of identical tech keywords across sections
    - Suspiciously dense keyword clusters (ratio of unique:total words)
    - Same phrase repeated verbatim across multiple job descriptions
    """

    RULE_CODE = "KEYWORD_001"
    RULE_NAME = "Duplicate Keyword Detection"
    CATEGORY = "Content Integrity"
    DEFAULT_WEIGHT = 15

    # A keyword appearing more than this many times is suspicious
    REPEAT_THRESHOLD = 8
    # Ratio of unique words to total words — below this is suspicious
    UNIQUE_RATIO_THRESHOLD = 0.35
    # Minimum word count to make the ratio meaningful
    MIN_WORD_COUNT = 100

    # Stop-words to exclude from repetition analysis
    _STOPWORDS: frozenset = frozenset([
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "did", "will", "would", "could", "should",
        "may", "might", "shall", "i", "we", "you", "he", "she", "they", "it",
        "my", "our", "your", "his", "her", "their", "its", "this", "that",
        "these", "those", "as", "if", "not", "no", "so", "up", "out", "than",
        "then", "when", "where", "which", "who", "how", "what", "year", "years",
        "experience", "project", "projects", "team", "worked", "work", "using",
        "used", "developed", "responsible", "development",
    ])

    def evaluate(self, parsed_data: Dict[str, Any], raw_text: str) -> RuleResult:
        if not raw_text or len(raw_text.split()) < self.MIN_WORD_COUNT:
            return self._pass(confidence=0.4, metadata={"reason": "insufficient_text"})

        issues: List[str] = []
        evidences: List[str] = []

        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.\-]{2,}\b", raw_text.lower())
        meaningful = [w for w in words if w not in self._STOPWORDS]

        if not meaningful:
            return self._pass(confidence=0.4)

        total = len(meaningful)
        unique = len(set(meaningful))
        unique_ratio = unique / total if total else 1.0

        # 1. Unique-word ratio check
        if unique_ratio < self.UNIQUE_RATIO_THRESHOLD and total >= self.MIN_WORD_COUNT:
            issues.append(
                f"Low unique-word ratio ({unique_ratio:.0%}) — possible keyword stuffing"
            )
            evidences.append(f"unique_ratio={unique_ratio:.2f}")

        # 2. High-frequency individual keyword check
        counts = Counter(meaningful)
        top_repeats: List[Tuple[str, int]] = [
            (word, cnt) for word, cnt in counts.most_common(20)
            if cnt >= self.REPEAT_THRESHOLD
        ]
        if top_repeats:
            examples = ", ".join(f"'{w}' ×{c}" for w, c in top_repeats[:4])
            issues.append(f"Repeated keywords detected: {examples}")
            evidences.append(examples)

        # 3. Duplicate job description sentences
        job_descs: List[str] = []
        for exp in (parsed_data.get("experience") or []):
            desc = exp.get("description") or exp.get("responsibilities") or ""
            if desc:
                job_descs.append(desc.strip().lower())

        if len(job_descs) >= 2:
            for i in range(len(job_descs)):
                for j in range(i + 1, len(job_descs)):
                    ratio = self._similarity_ratio(job_descs[i], job_descs[j])
                    if ratio > 0.85:
                        issues.append(
                            f"Job description entries {i+1} and {j+1} are {ratio:.0%} identical"
                        )
                        evidences.append(f"Duplicate job_desc blocks: entry {i+1} ≈ entry {j+1}")

        if not issues:
            return self._pass(
                confidence=0.9,
                metadata={"unique_ratio": round(unique_ratio, 3), "total_words": total},
            )

        return self._fail(
            title="Keyword Stuffing / ATS Gaming Detected",
            description=f"{len(issues)} content integrity issue(s): {'; '.join(issues[:3])}",
            severity="MEDIUM" if len(issues) == 1 else "HIGH",
            penalty=self.DEFAULT_WEIGHT,
            evidence="; ".join(evidences[:3]),
            confidence=0.8,
            recommendation="Review resume for ATS gaming; request unformatted version.",
            metadata={"issues": issues, "unique_ratio": round(unique_ratio, 3)},
        )

    @staticmethod
    def _similarity_ratio(a: str, b: str) -> float:
        """Jaccard similarity on word sets — O(n) and dependency-free."""
        sa, sb = set(a.split()), set(b.split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)
