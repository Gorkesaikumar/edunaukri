"""Django Admin configuration for Social Account management.

Provides a production-grade admin interface for managing OAuth-linked
social accounts across all providers (Google, LinkedIn, Microsoft, GitHub).

Uses a polymorphic GenericForeignKey for the user relationship, so the
admin display handles all user types (AdminUser, ITUser, ProfessorUser, etc.).
"""

from __future__ import annotations

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.social_auth.models import SocialAccount


# ---------------------------------------------------------------------------
# Inline — quick-link social accounts under the user change page
# ---------------------------------------------------------------------------


class SocialAccountInline(admin.TabularInline):
    """Inline admin for SocialAccount displayed on the User change page.

    Because ``SocialAccount`` uses a ``GenericForeignKey``, Django's
    automatic FK-based inline filtering does not apply.  We override
    ``get_queryset()`` to filter by ``content_type`` + ``object_id``
    matching the parent user.
    """

    model = SocialAccount
    extra = 0
    max_num = 10
    can_delete = True
    show_change_link = True

    fields = (
        "provider",
        "email",
        "user_domain",
        "is_verified",
        "last_login_at",
    )
    readonly_fields = (
        "provider",
        "email",
        "user_domain",
        "is_verified",
        "last_login_at",
    )

    def get_queryset(self, request):
        """Return empty queryset — real filtering is done in ``get_formset``."""
        return super().get_queryset(request).none()

    def get_formset(self, request, obj=None, **kwargs):
        """Return a formset filtered to the parent object's social accounts."""
        formset = super().get_formset(request, obj, **kwargs)
        if obj is not None:
            from django.contrib.contenttypes.models import ContentType

            ct = ContentType.objects.get_for_model(obj)
            formset.queryset = self.model.objects.filter(
                content_type=ct,
                object_id=obj.pk,
            )
        return formset

    def has_add_permission(self, request, obj=None) -> bool:
        """Social accounts should be linked via OAuth flow, not manually created."""
        return False


# ---------------------------------------------------------------------------
# Main ModelAdmin
# ---------------------------------------------------------------------------


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    """Production-ready admin for :class:`SocialAccount`.

    Designed for admin operators to:
    * Quickly find a social account by email, provider user ID, or user.
    * Filter by provider, domain, or verification status.
    * View OAuth token metadata (read-only for security).
    * Bulk-verify unverified social accounts.
    """

    # -- List view -------------------------------------------------------

    list_display = (
        "email",
        "colored_provider",
        "user_domain",
        "linked_user",
        "last_login_at",
        "is_verified_badge",
        "created_at",
    )
    list_display_links = ("email",)
    list_filter = (
        "provider",
        "user_domain",
        "is_verified",
    )
    date_hierarchy = "created_at"
    search_fields = (
        "email",
        "provider",
        "provider_user_id",
    )
    list_per_page = 50

    # -- Form view -------------------------------------------------------

    fieldsets = (
        (
            _("Identity"),
            {
                "fields": (
                    "email",
                    "provider",
                    "provider_user_id",
                ),
            },
        ),
        (
            _("Linked User (Polymorphic)"),
            {
                "fields": (
                    "user_domain",
                    "content_type",
                    "object_id",
                ),
                "description": _(
                    "The local user account this social login is linked to. "
                    "content_type identifies the model class, object_id is "
                    "the user's UUID. Changing these links the social profile "
                    "to a different user."
                ),
            },
        ),
        (
            _("Profile Data"),
            {
                "classes": ("collapse",),
                "fields": (
                    "display_name",
                    "profile_picture",
                ),
            },
        ),
        (
            _("OAuth Tokens (read-only)"),
            {
                "classes": ("collapse",),
                "fields": (
                    "access_token",
                    "refresh_token",
                    "token_expiry",
                ),
                "description": _(
                    "OAuth tokens are displayed for diagnostic purposes only. "
                    "Sensitive tokens are stored encrypted at rest in production."
                ),
            },
        ),
        (
            _("Activity"),
            {
                "fields": (
                    "is_verified",
                    "last_login_at",
                ),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )
    readonly_fields = (
        "access_token",
        "refresh_token",
        "token_expiry",
        "created_at",
        "updated_at",
        "last_login_at",
    )
    raw_id_fields = ("content_type",)  # raw_id for the FK; object_id is manual
    save_on_top = True

    # -- Actions ---------------------------------------------------------

    actions = (
        "mark_as_verified",
        "mark_as_unverified",
    )

    @admin.action(description=_("Mark selected accounts as verified"))
    def mark_as_verified(self, request, queryset):
        """Bulk-set the ``is_verified`` flag to ``True``."""
        updated = queryset.update(is_verified=True)
        self.message_user(
            request,
            _("%(count)d social account(s) marked as verified.") % {"count": updated},
        )

    @admin.action(description=_("Mark selected accounts as unverified"))
    def mark_as_unverified(self, request, queryset):
        """Bulk-set the ``is_verified`` flag to ``False``."""
        updated = queryset.update(is_verified=False)
        self.message_user(
            request,
            _("%(count)d social account(s) marked as unverified.") % {"count": updated},
        )

    # -- Display helpers -------------------------------------------------

    @admin.display(description=_("Provider"), ordering="provider")
    def colored_provider(self, obj: SocialAccount) -> str:
        """Render the provider name with a brand-coloured badge."""
        colours = {
            SocialAccount.ProviderChoices.GOOGLE: "#4285F4",
            SocialAccount.ProviderChoices.LINKEDIN: "#0A66C2",
            SocialAccount.ProviderChoices.MICROSOFT: "#00A4EF",
            SocialAccount.ProviderChoices.GITHUB: "#24292F",
        }
        colour = colours.get(obj.provider, "#6C757D")
        label = obj.get_provider_display()
        return format_html(
            '<span style="background-color: {colour}; color: #fff; '
            "padding: 2px 8px; border-radius: 3px; "
            'font-size: 0.85em; font-weight: 600;">{label}</span>',
            colour=colour,
            label=label,
        )

    @admin.display(description=_("User"))
    def linked_user(self, obj: SocialAccount) -> str:
        """Render the linked user as a clickable admin link.

        Works for any user model (AdminUser, ITUser, ProfessorUser, etc.)
        via the GenericForeignKey.
        """
        user = obj.user
        if user is None:
            return "—"
        try:
            url = reverse(
                f"admin:{user._meta.app_label}_{user._meta.model_name}_change",
                args=[user.pk],
            )
        except NoReverseMatch:
            return user.email or str(user.pk)[:8]
        return format_html(
            '<a href="{url}">{email}</a>',
            url=url,
            email=user.email or str(user.pk)[:8],
        )

    @admin.display(description=_("Verified"))
    def is_verified_badge(self, obj: SocialAccount) -> str:
        """Render a green checkmark or red cross for verification status."""
        if obj.is_verified:
            return format_html(
                '<span style="color: #28a745; font-weight: 600;">\u2714</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: 600;">\u2718</span>'
        )


