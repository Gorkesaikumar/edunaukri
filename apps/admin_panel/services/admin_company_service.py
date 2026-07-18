from apps.admin_panel.services.admin_audit import record_admin_action
from apps.core.services.base import BaseService


class AdminCompanyService(BaseService):
    def deactivate(self, company, *, admin_id, remarks: str = ""):
        company.is_active = False
        company.save(update_fields=["is_active"])
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.company.deactivated",
            entity_type="it_company",
            entity_id=company.pk,
        )
        return company
