from __future__ import annotations
import json
import logging
from src.parsers.base import BaseLLMParser, EXTRACTION_SYSTEM_PROMPT
from src.models import MetricOperator, Period, Severity, SLATerm

logger = logging.getLogger(__name__)


class AnthropicParser(BaseLLMParser):
    """Extracts SLA terms using Anthropic's Claude API."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package is required. Install with: pip install anthropic"
                )
        return self._client

    def extract_sla_terms(self, contract_text: str) -> list[SLATerm]:
        client = self._get_client()
        logger.info("AnthropicParser: extracting SLA terms via %s", self.model)

        message = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Extract all SLA terms from this contract:\n\n{contract_text}",
                }
            ],
        )

        raw = message.content[0].text.strip()
        return _parse_llm_response(raw)

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception:
            return False


def _parse_llm_response(raw: str) -> list[SLATerm]:
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse LLM response as JSON: %s\nRaw: %s", exc, raw[:500])
        return []

    terms: list[SLATerm] = []
    for item in data:
        try:
            terms.append(
                SLATerm(
                    name=item["name"],
                    metric=item["metric"],
                    operator=MetricOperator(item["operator"]),
                    threshold=float(item["threshold"]),
                    period=Period(item["period"]),
                    severity=Severity(item.get("severity", "warning")),
                    description=item.get("description", ""),
                )
            )
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed SLA term %s: %s", item, exc)

    logger.info("Extracted %d SLA terms", len(terms))
    return terms
