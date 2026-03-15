from __future__ import annotations
import logging
from src.parsers.base import BaseLLMParser
from src.models import MetricOperator, Period, Severity, SLATerm

logger = logging.getLogger(__name__)

# Pre-defined SLA terms per vendor for offline/test use
MOCK_TERMS: dict[str, list[dict]] = {
    "vendor_a": [
        {
            "name": "api_uptime",
            "metric": "uptime_percentage",
            "operator": ">=",
            "threshold": 99.5,
            "period": "per_month",
            "severity": "critical",
            "description": "API uptime must be >= 99.5% per month.",
        },
        {
            "name": "rate_limit_hourly",
            "metric": "api_calls_per_hour",
            "operator": "<=",
            "threshold": 10000.0,
            "period": "per_hour",
            "severity": "warning",
            "description": "API calls must not exceed 10,000 per hour.",
        },
        {
            "name": "response_time_p95",
            "metric": "response_time_ms_p95",
            "operator": "<=",
            "threshold": 200.0,
            "period": "per_day",
            "severity": "warning",
            "description": "P95 response time must be <= 200ms per day.",
        },
        {
            "name": "error_rate",
            "metric": "error_rate_percentage",
            "operator": "<=",
            "threshold": 1.0,
            "period": "per_day",
            "severity": "critical",
            "description": "Error rate must not exceed 1% per day.",
        },
    ],
    "vendor_b": [
        {
            "name": "storage_uptime",
            "metric": "uptime_percentage",
            "operator": ">=",
            "threshold": 99.9,
            "period": "per_month",
            "severity": "critical",
            "description": "Storage uptime must be >= 99.9% per month.",
        },
        {
            "name": "api_daily_limit",
            "metric": "api_calls_per_day",
            "operator": "<=",
            "threshold": 50000.0,
            "period": "per_day",
            "severity": "warning",
            "description": "API calls must not exceed 50,000 per day.",
        },
        {
            "name": "latency_p50",
            "metric": "latency_ms_p50",
            "operator": "<=",
            "threshold": 100.0,
            "period": "per_day",
            "severity": "warning",
            "description": "P50 latency must be <= 100ms per day.",
        },
        {
            "name": "data_transfer_cap",
            "metric": "data_transfer_gb_per_day",
            "operator": "<=",
            "threshold": 1000.0,
            "period": "per_day",
            "severity": "critical",
            "description": "Data transfer must not exceed 1TB per day.",
        },
    ],
}


class MockLLMParser(BaseLLMParser):
    """
    Returns hardcoded SLA terms without calling any LLM.
    Useful for testing, demos, and CI pipelines.
    """

    def __init__(self, vendor_id: str | None = None):
        self.vendor_id = vendor_id

    def extract_sla_terms(self, contract_text: str) -> list[SLATerm]:
        logger.info("MockLLMParser: returning pre-defined SLA terms")

        # Try to detect vendor from contract text or use provided vendor_id
        resolved_vendor = self.vendor_id
        if resolved_vendor is None:
            for vid in MOCK_TERMS:
                if vid in contract_text.lower():
                    resolved_vendor = vid
                    break

        raw_terms = MOCK_TERMS.get(resolved_vendor or "vendor_a", MOCK_TERMS["vendor_a"])
        return [_dict_to_sla_term(t) for t in raw_terms]


def _dict_to_sla_term(d: dict) -> SLATerm:
    return SLATerm(
        name=d["name"],
        metric=d["metric"],
        operator=MetricOperator(d["operator"]),
        threshold=float(d["threshold"]),
        period=Period(d["period"]),
        severity=Severity(d["severity"]),
        description=d.get("description", ""),
    )
