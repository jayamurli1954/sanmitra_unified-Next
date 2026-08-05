from __future__ import annotations

import time
from decimal import Decimal, InvalidOperation

import httpx

from app.config import get_settings
from app.modules.office_ai.ai.provider_base import ProviderResult


def _estimate_cost(tokens_in: int | None, tokens_out: int | None) -> str | None:
    settings = get_settings()
    try:
        in_rate = Decimal(settings.OFFICEMITRA_AI_COST_PER_1M_INPUT)
        out_rate = Decimal(settings.OFFICEMITRA_AI_COST_PER_1M_OUTPUT)
    except InvalidOperation:
        return None
    total = Decimal("0")
    if tokens_in:
        total += (Decimal(tokens_in) / Decimal("1000000")) * in_rate
    if tokens_out:
        total += (Decimal(tokens_out) / Decimal("1000000")) * out_rate
    if total <= 0:
        return None
    return f"{total.quantize(Decimal('0.000001'))}"


class ClaudeProvider:
    name = "claude"

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> ProviderResult:
        settings = get_settings()
        model = settings.OFFICEMITRA_AI_MODEL
        token_cap = max_tokens or settings.OFFICEMITRA_AI_MAX_TOKENS
        body = {
            "model": model,
            "max_tokens": token_cap,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{settings.ANTHROPIC_API_BASE.rstrip('/')}/messages",
                    headers=headers,
                    json=body,
                )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if response.status_code >= 400:
                return ProviderResult(
                    text="",
                    provider=self.name,
                    model=model,
                    success=False,
                    latency_ms=latency_ms,
                    error_code=f"http_{response.status_code}",
                )
            payload = response.json()
            content = payload.get("content") or []
            text = "\n".join(
                str(part.get("text") or "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
            usage = payload.get("usage") or {}
            tokens_in = usage.get("input_tokens")
            tokens_out = usage.get("output_tokens")
            return ProviderResult(
                text=text,
                provider=self.name,
                model=model,
                success=bool(text),
                tokens_in=int(tokens_in) if tokens_in is not None else None,
                tokens_out=int(tokens_out) if tokens_out is not None else None,
                latency_ms=latency_ms,
                estimated_cost=_estimate_cost(
                    int(tokens_in) if tokens_in is not None else None,
                    int(tokens_out) if tokens_out is not None else None,
                ),
                error_code=None if text else "empty_response",
                raw_usage=dict(usage) if isinstance(usage, dict) else {},
            )
        except Exception:
            latency_ms = int((time.perf_counter() - started) * 1000)
            return ProviderResult(
                text="",
                provider=self.name,
                model=model,
                success=False,
                latency_ms=latency_ms,
                error_code="provider_exception",
            )
