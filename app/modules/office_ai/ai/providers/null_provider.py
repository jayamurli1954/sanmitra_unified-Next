from __future__ import annotations

from app.modules.office_ai.ai.provider_base import ProviderResult


class NullProvider:
    name = "null"

    def __init__(self, reason: str = "unavailable") -> None:
        self.reason = reason

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> ProviderResult:
        return ProviderResult(
            text="",
            provider=self.name,
            model="none",
            success=False,
            latency_ms=0,
            error_code=self.reason,
        )
