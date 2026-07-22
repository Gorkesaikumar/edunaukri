"""Rule Registry — single source of truth for all registered fraud detection rules.

Open/Closed Principle:
- To ADD a new rule: subclass BaseResumeRule, then append to RULE_REGISTRY.
- To REMOVE a rule: remove it from RULE_REGISTRY.
- Never modify the engine (ResumeFraudRuleEngine) to add rules.
"""

from __future__ import annotations

from apps.resume_trust.services.rules.base_rule import BaseResumeRule
from apps.resume_trust.services.rules.certification_validation_rule import CertificationValidationRule
from apps.resume_trust.services.rules.company_validation_rule import CompanyValidationRule
from apps.resume_trust.services.rules.contact_validation_rule import ContactValidationRule
from apps.resume_trust.services.rules.duplicate_keyword_rule import DuplicateKeywordRule
from apps.resume_trust.services.rules.education_validation_rule import EducationValidationRule
from apps.resume_trust.services.rules.resume_completeness_rule import ResumeCompletenessRule
from apps.resume_trust.services.rules.skill_inflation_rule import SkillInflationRule
from apps.resume_trust.services.rules.timeline_validation_rule import TimelineValidationRule

# ============================================================
# RULE_REGISTRY — ordered list of active rule instances.
# Execution order matters only for performance (cheap rules first).
# Add new rules here. Never touch ResumeFraudRuleEngine.
# ============================================================
RULE_REGISTRY: list[BaseResumeRule] = [
    ContactValidationRule(),       # cheapest — field presence checks
    ResumeCompletenessRule(),      # cheap — section presence
    TimelineValidationRule(),      # medium — date arithmetic
    EducationValidationRule(),     # medium — keyword + pattern match
    CompanyValidationRule(),       # medium — name + date analysis
    CertificationValidationRule(), # medium — cert list validation
    SkillInflationRule(),          # heavier — set intersections
    DuplicateKeywordRule(),        # heavier — word frequency analysis
]
