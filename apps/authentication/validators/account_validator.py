from django.conf import settings

from apps.accounts.constants.enums import AccountStatus


def get_account_access_block_reason(user) -> str | None:
    """Return a machine-readable reason when the account must not receive access."""
    if getattr(user, "is_locked", False):
        return "account_locked"
    if not user.is_active or getattr(user, "is_deleted", False):
        return "inactive_account"
    if user.account_status in (AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED):
        return "account_suspended"
    if (
        getattr(settings, "AUTH_REQUIRE_EMAIL_VERIFICATION", False)
        and hasattr(user, "email_verified")
        and not user.email_verified
    ):
        return "email_unverified"
    return None
