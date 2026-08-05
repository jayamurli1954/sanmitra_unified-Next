"""Lightweight OfficeMitra AI eval harness — runs against fixtures without live providers by default."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.office_ai.ai.orchestrator import build_daily_brief, generate_tasks, summarize_email

FIXTURE_ROOT = Path(__file__).resolve().parent / "ai" / "officemitra"


def _load(folder: str) -> list[dict]:
    path = FIXTURE_ROOT / folder
    if not path.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(path.glob("*.json"))]


@pytest.mark.asyncio
async def test_ai_eval_tasks_with_fake_provider(monkeypatch):
    from app.modules.office_ai.ai.provider_base import ProviderResult

    class FakeProvider:
        name = "fake"

        async def complete(self, *, system: str, user: str, max_tokens: int | None = None):
            return ProviderResult(
                text='[{"title":"Call ACME about invoice 1042"},{"title":"Draft payment reminder"}]',
                provider="fake",
                model="fake-1",
                success=True,
                tokens_in=10,
                tokens_out=20,
                latency_ms=5,
                estimated_cost="0.000001",
            )

    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.get_ai_provider", lambda: FakeProvider())

    async def fake_telemetry(**kwargs):
        return "t1"

    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.record_telemetry", fake_telemetry)

    for fixture in _load("tasks"):
        result = await generate_tasks(tenant_id="eval", text=fixture["input"])
        assert result["ai_available"] is True
        assert len(result["tasks"]) >= fixture["expect"]["tasks_min"]
        joined = " ".join(t["title"].lower() for t in result["tasks"])
        assert any(token.lower() in joined for token in fixture["expect"]["titles_contain_any"])


@pytest.mark.asyncio
async def test_ai_eval_summaries_with_fake_provider(monkeypatch):
    from app.modules.office_ai.ai.provider_base import ProviderResult

    class FakeProvider:
        name = "fake"

        async def complete(self, *, system: str, user: str, max_tokens: int | None = None):
            return ProviderResult(
                text='{"summary":"Ravi asks for signed PO by Friday and delivery confirmation Monday.","action_items":["Send signed PO by Friday","Confirm Monday delivery"]}',
                provider="fake",
                model="fake-1",
                success=True,
                latency_ms=4,
            )

    async def _async_id(**kwargs):
        return "t2"

    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.get_ai_provider", lambda: FakeProvider())
    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.record_telemetry", _async_id)

    for fixture in _load("summaries"):
        result = await summarize_email(tenant_id="eval", text=fixture["input"])
        assert result["ai_available"] is True
        summary = (result["summary"] or "").lower()
        assert any(token.lower() in summary for token in fixture["expect"]["summary_contains_any"])
        assert len(result["action_items"]) >= fixture["expect"]["action_items_min"]


@pytest.mark.asyncio
async def test_ai_eval_brief_deterministic_fallback(monkeypatch):
    from app.modules.office_ai.ai.providers.null_provider import NullProvider

    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.get_ai_provider", lambda: NullProvider(reason="eval"))

    async def _async_id(**kwargs):
        return "t3"

    monkeypatch.setattr("app.modules.office_ai.ai.orchestrator.record_telemetry", _async_id)

    for fixture in _load("briefs"):
        result = await build_daily_brief(tenant_id="eval", facts=fixture["facts"])
        content = (result["content"] or "").lower()
        assert any(token.lower() in content for token in fixture["expect"]["content_contains_any"])
