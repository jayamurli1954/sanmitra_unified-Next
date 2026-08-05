from __future__ import annotations

from app.config import get_settings
from app.modules.office_ai.ai.provider_base import AIProvider, ProviderResult
from app.modules.office_ai.ai.providers.claude import ClaudeProvider
from app.modules.office_ai.ai.providers.null_provider import NullProvider


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if not settings.OFFICEMITRA_AI_ENABLED:
        return NullProvider(reason="disabled")
    provider = str(settings.OFFICEMITRA_AI_PROVIDER or "claude").strip().lower()
    if provider in {"claude", "anthropic"}:
        if not settings.ANTHROPIC_API_KEY:
            return NullProvider(reason="missing_api_key")
        return ClaudeProvider()
    if provider in {"null", "none", "off"}:
        return NullProvider(reason="configured_null")
    return NullProvider(reason=f"unknown_provider:{provider}")


__all__ = ["AIProvider", "ProviderResult", "get_ai_provider"]
