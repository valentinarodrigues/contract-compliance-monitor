from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from src.models import LogEvent


class BaseLogSource(ABC):
    """Abstract interface for all log ingestion adapters."""

    @abstractmethod
    def fetch_logs(
        self, vendor_id: str, start_time: datetime, end_time: datetime
    ) -> list[LogEvent]:
        """Fetch log events for a vendor within the given time range."""
        ...

    @abstractmethod
    def get_vendor_ids(self) -> list[str]:
        """Return all vendor IDs known to this log source."""
        ...

    def health_check(self) -> bool:
        """Optional: verify connectivity to the underlying source."""
        return True
