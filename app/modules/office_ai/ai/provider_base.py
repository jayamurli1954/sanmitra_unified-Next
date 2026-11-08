from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


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


@dataclass
class VisionImage:
    """A single image page handed to a vision-capable provider.

    ``data_b64`` is the base64-encoded image bytes; ``media_type`` is an image
    MIME type the provider accepts (image/png, image/jpeg, image/webp).
    """

    media_type: str
    data_b64: str


@runtime_checkable
class AIProvider(Protocol):
    name: str

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> ProviderResult: ...

    async def complete_vision(
        self,
        *,
        system: str,
        user: str,
        images: list[VisionImage],
        max_tokens: int | None = None,
    ) -> ProviderResult: ...
