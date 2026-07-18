from django.core.exceptions import ValidationError

from apps.admin_panel.services.admin_report_service import VALID_REPORT_TYPES


def validate_report_type(report_type: str) -> None:
    if report_type not in VALID_REPORT_TYPES:
        raise ValidationError(
            f"Invalid report type. Allowed: {', '.join(sorted(VALID_REPORT_TYPES))}"
        )


def validate_user_domain(domain: str) -> None:
    if domain not in {"it", "professor", "college", "admin"}:
        raise ValidationError("Invalid user domain.")


def validate_lifecycle_action(action: str) -> None:
    if action not in {"activate", "suspend", "deactivate"}:
        raise ValidationError("Invalid lifecycle action.")
