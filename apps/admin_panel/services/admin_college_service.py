from apps.admin_panel.services.admin_audit import record_admin_action
from apps.core.services.base import BaseService


class AdminCollegeService(BaseService):
    def deactivate(self, college, *, admin_id, remarks: str = ""):
        college.is_active = False
        college.save(update_fields=["is_active"])
        record_admin_action(
            admin_id=admin_id,
            event_type="admin.college.deactivated",
            entity_type="faculty_college",
            entity_id=college.pk,
        )
        return college
