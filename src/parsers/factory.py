from __future__ import annotations
from src.parsers.base import BaseLLMParser


def create_parser(provider: str | None = None, vendor_id: str | None = None) -> BaseLLMParser:
    """
    Factory that returns the appropriate LLM contract parser.

    provider values (overrides LLM_PROVIDER env var):
      mock       – hardcoded SLA terms, no external calls
      anthropic  – Claude via Anthropic API
      openai     – Any OpenAI-compatible endpoint (LibertyGPT, Azure, etc.)
    """
    from config import settings

    provider = (provider or settings.LLM_PROVIDER).lower()

    if provider == "mock":
        from src.parsers.mock_parser import MockLLMParser
        return MockLLMParser(vendor_id=vendor_id)

    if provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required for the anthropic provider")
        from src.parsers.anthropic_parser import AnthropicParser
        return AnthropicParser(
            api_key=settings.ANTHROPIC_API_KEY,
            model=settings.ANTHROPIC_MODEL,
        )

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for the openai provider")
        from src.parsers.openai_parser import OpenAIParser
        return OpenAIParser(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            base_url=settings.OPENAI_BASE_URL or None,
        )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. Choose: mock | anthropic | openai"
    )
