from apps.core.exceptions.domain_exceptions import BusinessLogicException
from apps.core.services.base import BaseService


class BusinessRule(BaseService):
    """Base class for composable business rules."""

    message = "Business rule violated."

    def check(self, context: dict | None = None) -> None:
        if not self.is_satisfied(context or {}):
            raise BusinessLogicException(self.message)

    def is_satisfied(self, context: dict) -> bool:
        raise NotImplementedError

    def __call__(self, context: dict | None = None) -> None:
        self.check(context)


class BusinessRuleSet(BaseService):
    """Run a sequence of business rules."""

    def __init__(self, rules: list[BusinessRule] | None = None):
        self.rules = rules or []

    def evaluate(self, context: dict | None = None) -> None:
        for rule in self.rules:
            rule.check(context)
