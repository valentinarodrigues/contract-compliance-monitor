from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from src.ingestion.base import BaseLogSource
from src.models import LogEvent

logger = logging.getLogger(__name__)


class LocalFileLogSource(BaseLogSource):
    """
    Reads log events from JSON files in a directory.

    Expected file naming: {vendor_id}_logs.json
    Expected JSON format: list of objects with fields:
      timestamp (ISO 8601), vendor_id, metric, value, metadata (optional)
    """

    def __init__(self, log_dir: str = "data/sample_logs"):
        self.log_dir = Path(log_dir)

    def get_vendor_ids(self) -> list[str]:
        vendor_ids = []
        for f in self.log_dir.glob("*_logs.json"):
            vendor_ids.append(f.stem.replace("_logs", ""))
        return vendor_ids

    def fetch_logs(
        self, vendor_id: str, start_time: datetime, end_time: datetime
    ) -> list[LogEvent]:
        log_file = self.log_dir / f"{vendor_id}_logs.json"
        if not log_file.exists():
            logger.warning("Log file not found: %s", log_file)
            return []

        try:
            raw = json.loads(log_file.read_text())
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse %s: %s", log_file, exc)
            return []

        events: list[LogEvent] = []
        for record in raw:
            ts = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
            # Strip timezone for naive comparison
            ts = ts.replace(tzinfo=None)
            if not (start_time <= ts <= end_time):
                continue
            events.append(
                LogEvent(
                    timestamp=ts,
                    vendor_id=record.get("vendor_id", vendor_id),
                    metric=record["metric"],
                    value=float(record["value"]),
                    metadata=record.get("metadata", {}),
                )
            )

        return events

    def health_check(self) -> bool:
        return self.log_dir.exists()
