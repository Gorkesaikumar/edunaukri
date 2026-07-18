import csv
import io
import json
from typing import Any


class AdminExportService:
    """CSV and Excel export helpers for admin reports."""

    def to_csv(self, rows: list[dict], fieldnames: list[str] | None = None) -> str:
        if not rows:
            return ""
        fieldnames = fieldnames or list(rows[0].keys())
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()

    def flatten_dict(self, data: dict, prefix: str = "") -> list[dict]:
        rows = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                rows.extend(self.flatten_dict(value, full_key))
            else:
                rows.append({"metric": full_key, "value": value})
        return rows

    def to_excel_bytes(
        self, rows: list[dict], fieldnames: list[str] | None = None
    ) -> bytes:
        try:
            from openpyxl import Workbook
        except ImportError:
            return self.to_csv(rows, fieldnames).encode("utf-8")
        if not rows:
            rows = [{"message": "No data"}]
        fieldnames = fieldnames or list(rows[0].keys())
        wb = Workbook()
        ws = wb.active
        ws.append(fieldnames)
        for row in rows:
            ws.append([row.get(f) for f in fieldnames])
        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def export_report(
        self, data: dict, *, export_as: str = "json"
    ) -> tuple[bytes | str, str, str]:
        export_as = export_as.lower()
        if export_as == "csv":
            rows = self.flatten_dict(data)
            return self.to_csv(rows), "text/csv", "report.csv"
        if export_as in ("xlsx", "excel"):
            rows = self.flatten_dict(data)
            return (
                self.to_excel_bytes(rows),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "report.xlsx",
            )
        return (
            json.dumps(data, indent=2, default=str).encode("utf-8"),
            "application/json",
            "report.json",
        )
