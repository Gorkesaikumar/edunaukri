from django.contrib import admin

from apps.authentication.models import AuthToken, LoginAttempt


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ("email", "domain", "purpose", "expires_at", "used_at", "is_deleted")
    list_filter = ("domain", "purpose", "is_deleted")
    readonly_fields = ("token_hash", "created_at", "updated_at")


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "domain",
        "result",
        "failure_reason",
        "attempted_at",
        "ip_address",
    )
    list_filter = ("domain", "result")
    readonly_fields = ("created_at", "updated_at")
