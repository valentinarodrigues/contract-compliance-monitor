from __future__ import annotations
import json
import logging
from src.parsers.base import BaseLLMParser, EXTRACTION_SYSTEM_PROMPT
from src.parsers.anthropic_parser import _parse_llm_response
from src.models import SLATerm

logger = logging.getLogger(__name__)


class OpenAIParser(BaseLLMParser):
    """
    Extracts SLA terms using any OpenAI-compatible API.
    Works with: OpenAI, LibertyGPT, Azure OpenAI, Ollama, LM Studio, etc.
    Set OPENAI_BASE_URL to point to your provider's endpoint.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI

                kwargs: dict = {"api_key": self.api_key}
                if self.base_url:
                    kwargs["base_url"] = self.base_url
                self._client = OpenAI(**kwargs)
            except ImportError:
                raise RuntimeError(
                    "openai package is required. Install with: pip install openai"
                )
        return self._client

    def extract_sla_terms(self, contract_text: str) -> list[SLATerm]:
        client = self._get_client()
        logger.info("OpenAIParser: extracting SLA terms via %s", self.model)

        response = client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Extract all SLA terms from this contract and return as JSON array "
                        f"under key 'terms':\n\n{contract_text}"
                    ),
                },
            ],
            max_tokens=2048,
        )

        raw = response.choices[0].message.content or ""
        # Unwrap {"terms": [...]} wrapper if present
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "terms" in parsed:
                raw = json.dumps(parsed["terms"])
        except json.JSONDecodeError:
            pass

        return _parse_llm_response(raw)

    def health_check(self) -> bool:
        try:
            client = self._get_client()
            client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False
