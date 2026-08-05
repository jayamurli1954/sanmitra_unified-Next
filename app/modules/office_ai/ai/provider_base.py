from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class ProviderResult:
    text: str
    provider: str
    model: str
    success: bool
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_ms: int = 0
    estimated_cost: str | None = None
    error_code: str | None = None
    raw_usage: dict = field(default_factory=dict)


class AIProvider(Protocol):
    name: str

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> ProviderResult: ...
