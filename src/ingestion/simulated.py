from __future__ import annotations
import random
from datetime import datetime, timedelta
from src.ingestion.base import BaseLogSource
from src.models import LogEvent

# Vendor definitions: vendor_id -> (vendor_name, metrics with normal ranges)
VENDOR_PROFILES: dict[str, dict] = {
    "vendor_a": {
        "name": "DataStream Inc.",
        "metrics": {
            "api_calls_per_hour": {"normal": (5000, 9000), "spike": 12000},
            "uptime_percentage": {"normal": (99.5, 100.0), "spike": 98.0},
            "response_time_ms_p95": {"normal": (100, 180), "spike": 350},
            "error_rate_percentage": {"normal": (0.1, 0.8), "spike": 2.5},
        },
    },
    "vendor_b": {
        "name": "CloudVault Ltd.",
        "metrics": {
            "api_calls_per_day": {"normal": (20000, 45000), "spike": 60000},
            "uptime_percentage": {"normal": (99.8, 100.0), "spike": 99.0},
            "latency_ms_p50": {"normal": (40, 90), "spike": 150},
            "data_transfer_gb_per_day": {"normal": (200, 800), "spike": 1200},
        },
    },
}


class SimulatedLogSource(BaseLogSource):
    """
    Generates realistic synthetic log events.
    Randomly injects violations to exercise the monitoring engine.
    """

    def __init__(self, violation_probability: float = 0.08):
        self.violation_probability = violation_probability

    def get_vendor_ids(self) -> list[str]:
        return list(VENDOR_PROFILES.keys())

    def fetch_logs(
        self, vendor_id: str, start_time: datetime, end_time: datetime
    ) -> list[LogEvent]:
        if vendor_id not in VENDOR_PROFILES:
            return []

        profile = VENDOR_PROFILES[vendor_id]
        events: list[LogEvent] = []

        # Generate one event per metric per 5-minute interval
        current = start_time
        interval = timedelta(minutes=5)

        while current <= end_time:
            for metric, ranges in profile["metrics"].items():
                inject_violation = random.random() < self.violation_probability

                if inject_violation:
                    value = float(ranges["spike"])
                    # For uptime, spike means drop below threshold
                    if "uptime" in metric and isinstance(ranges["spike"], float):
                        value = ranges["spike"]
                else:
                    low, high = ranges["normal"]
                    value = round(random.uniform(low, high), 2)

                events.append(
                    LogEvent(
                        timestamp=current,
                        vendor_id=vendor_id,
                        metric=metric,
                        value=value,
                        metadata={
                            "source": "simulated",
                            "vendor_name": profile["name"],
                            "injected_violation": inject_violation,
                        },
                    )
                )
            current += interval

        return events
