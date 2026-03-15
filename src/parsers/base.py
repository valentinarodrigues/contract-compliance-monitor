from __future__ import annotations
from abc import ABC, abstractmethod
from src.models import SLATerm

# The structured prompt used by all LLM parsers.
EXTRACTION_SYSTEM_PROMPT = """
You are a contract compliance analyst. Extract SLA (Service Level Agreement) terms
from vendor contracts and return them as structured JSON.

For each SLA term you find, return an object with these fields:
  - name:        short identifier, snake_case (e.g. "api_uptime", "rate_limit_hourly")
  - metric:      the measurable attribute (e.g. "uptime_percentage", "api_calls_per_hour")
  - operator:    one of: "<=", ">=", "==", "<", ">"
  - threshold:   numeric value (float)
  - period:      one of: "per_minute", "per_hour", "per_day", "per_month", "rolling_24h"
  - severity:    "critical" if breach risks the contract, otherwise "warning"
  - description: one-sentence human-readable summary

Return ONLY a JSON array of these objects — no markdown, no explanation.
If no SLA terms are found, return an empty array [].
""".strip()


class BaseLLMParser(ABC):
    """Abstract interface for all LLM-based contract parsers."""

    @abstractmethod
    def extract_sla_terms(self, contract_text: str) -> list[SLATerm]:
        """Parse contract text and return structured SLA terms."""
        ...

    def health_check(self) -> bool:
        """Optional: verify the LLM provider is reachable."""
        return True
