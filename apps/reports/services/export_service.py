"""CSV/JSON export helpers for report data."""

import csv
import io
import json
from typing import Any


class ExportService:
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
        """Flatten nested dict into key-value rows for CSV export."""
        rows = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                rows.extend(self.flatten_dict(value, full_key))
            else:
                rows.append({"metric": full_key, "value": value})
        return rows

    def to_json_bytes(self, data: Any) -> bytes:
        return json.dumps(data, indent=2, default=str).encode("utf-8")
