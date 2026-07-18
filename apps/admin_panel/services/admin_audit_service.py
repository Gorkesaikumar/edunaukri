from apps.admin_panel.selectors.audit_selector import AuditSelector
from apps.admin_panel.services.admin_export_service import AdminExportService
from apps.audit.api.v1.serializers import AuditEventSerializer
from apps.core.services.base import BaseService


class AdminAuditService(BaseService):
    def __init__(self):
        self.selector = AuditSelector()
        self.export = AdminExportService()

    def list_events(self, **filters):
        return self.selector.search(**filters)

    def export_events(self, *, export_as: str = "csv", **filters):
        events = self.list_events(**filters)[:5000]
        rows = AuditEventSerializer(events, many=True).data
        if export_as == "csv":
            return self.export.to_csv(rows), "text/csv", "audit-logs.csv"
        return (
            self.export.to_excel_bytes(rows),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "audit-logs.xlsx",
        )
