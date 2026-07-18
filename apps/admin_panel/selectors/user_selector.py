from apps.accounts.constants.enums import AccountStatus
from apps.accounts.models.admin_user import AdminUser
from apps.accounts.models.college_user import CollegeUser
from apps.accounts.models.it_user import ITUser
from apps.accounts.models.professor_user import ProfessorUser
from apps.accounts.repositories.user_repository import DOMAIN_USER_MODELS


class UserSelector:
    """Cross-domain user listing for admin panel."""

    DOMAIN_MODELS = {
        "it": ITUser,
        "professor": ProfessorUser,
        "college": CollegeUser,
        "admin": AdminUser,
    }

    def list_users(
        self,
        *,
        domain: str | None = None,
        is_active: bool | None = None,
        account_status: str | None = None,
        search: str | None = None,
        org_id: str | None = None,
    ):
        domains = [domain] if domain else list(self.DOMAIN_MODELS.keys())
        results = []
        for dom in domains:
            model = self.DOMAIN_MODELS.get(dom)
            if not model:
                continue
            qs = model.objects.filter(is_deleted=False)
            if is_active is not None:
                qs = qs.filter(is_active=is_active)
            if account_status:
                qs = qs.filter(account_status=account_status)
            if search:
                qs = qs.filter(email__icontains=search)
            if org_id:
                if dom == "it":
                    qs = qs.filter(recruiter_profile__company_memberships__company_id=org_id)
                elif dom == "college":
                    qs = qs.filter(college_memberships__college_id=org_id)
            for user in qs.order_by("-created_at")[:500]:
                results.append(self._serialize_user(user, dom))
        return sorted(results, key=lambda u: u["created_at"], reverse=True)

    def get_user(self, *, domain: str, user_id):
        model = self.DOMAIN_MODELS.get(domain)
        if not model:
            return None
        user = model.objects.filter(pk=user_id, is_deleted=False).first()
        if not user:
            return None
        return self._serialize_user(user, domain, detailed=True)

    def _serialize_user(self, user, domain: str, *, detailed: bool = False) -> dict:
        data = {
            "id": str(user.pk),
            "domain": domain,
            "email": user.email,
            "is_active": user.is_active,
            "account_status": getattr(user, "account_status", AccountStatus.ACTIVE),
            "email_verified": getattr(user, "email_verified", False),
            "created_at": user.created_at.isoformat(),
        }
        if detailed:
            data["last_login"] = (
                user.last_login.isoformat() if user.last_login else None
            )
            data["is_staff"] = getattr(user, "is_staff", False)
            data["is_superuser"] = getattr(user, "is_superuser", False)
        return data
