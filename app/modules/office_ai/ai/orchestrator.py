from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.modules.office_ai.ai import get_ai_provider
from app.modules.office_ai.ai import metrics as ai_metrics
from app.modules.office_ai.ai.provider_base import ProviderResult
from app.modules.office_ai.ai.telemetry import record_telemetry

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

PROMPT_GENERATE_TASKS = "generate_tasks_v1"
PROMPT_SUMMARIZE_EMAIL = "summarize_email_v1"
PROMPT_DAILY_BRIEF = "daily_brief_v1"


def load_prompt(version_id: str) -> str:
    path = _PROMPTS_DIR / f"{version_id}.txt"
    return path.read_text(encoding="utf-8").strip()


def _extract_json(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", raw)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


async def _complete(
    *,
    tenant_id: str,
    feature: str,
    prompt_version: str,
    system: str,
    user: str,
    user_id: str | None,
) -> tuple[ProviderResult, str]:
    provider = get_ai_provider()
    result = await provider.complete(system=system, user=user)
    ai_metrics.observe_latency(f"officemitra.{feature}.latency", result.latency_ms)
    if result.success:
        ai_metrics.incr(f"officemitra.{feature}.success")
    else:
        ai_metrics.incr(f"officemitra.{feature}.failure")
    telemetry_id = await record_telemetry(
        tenant_id=tenant_id,
        feature=feature,
        prompt_version=prompt_version,
        result=result,
        user_id=user_id,
    )
    return result, telemetry_id


async def generate_tasks(
    *,
    tenant_id: str,
    text: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    prompt_version = PROMPT_GENERATE_TASKS
    system = load_prompt(prompt_version)
    result, telemetry_id = await _complete(
        tenant_id=tenant_id,
        feature="tasks",
        prompt_version=prompt_version,
        system=system,
        user=text.strip(),
        user_id=user_id,
    )
    tasks: list[dict[str, Any]] = []
    if result.success:
        parsed = _extract_json(result.text)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict) and str(item.get("title") or "").strip():
                    tasks.append(
                        {
                            "title": str(item.get("title")).strip()[:500],
                            "due_date": item.get("due_date"),
                        }
                    )
                elif isinstance(item, str) and item.strip():
                    tasks.append({"title": item.strip()[:500], "due_date": None})
    return {
        "ai_available": bool(result.success),
        "tasks": tasks,
        "prompt_version": prompt_version,
        "telemetry_id": telemetry_id,
        "provider": result.provider,
        "model": result.model,
        "error_code": result.error_code,
        "advisory": "AI-suggested tasks are drafts for human review.",
    }


async def summarize_email(
    *,
    tenant_id: str,
    text: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    prompt_version = PROMPT_SUMMARIZE_EMAIL
    system = load_prompt(prompt_version)
    result, telemetry_id = await _complete(
        tenant_id=tenant_id,
        feature="email",
        prompt_version=prompt_version,
        system=system,
        user=text.strip(),
        user_id=user_id,
    )
    summary = ""
    action_items: list[str] = []
    if result.success:
        parsed = _extract_json(result.text)
        if isinstance(parsed, dict):
            summary = str(parsed.get("summary") or "").strip()
            raw_items = parsed.get("action_items") or []
            if isinstance(raw_items, list):
                action_items = [str(item).strip() for item in raw_items if str(item).strip()]
        if not summary:
            summary = result.text.strip()
    return {
        "ai_available": bool(result.success and summary),
        "summary": summary,
        "action_items": action_items,
        "prompt_version": prompt_version,
        "telemetry_id": telemetry_id,
        "provider": result.provider,
        "model": result.model,
        "error_code": result.error_code,
        "advisory": "Email summaries are advisory and not legal or financial advice.",
    }


async def build_daily_brief(
    *,
    tenant_id: str,
    facts: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:
    prompt_version = PROMPT_DAILY_BRIEF
    system = load_prompt(prompt_version)
    user_payload = json.dumps(facts, ensure_ascii=False, default=str, indent=2)
    result, telemetry_id = await _complete(
        tenant_id=tenant_id,
        feature="brief",
        prompt_version=prompt_version,
        system=system,
        user=user_payload,
        user_id=user_id,
    )
    content = result.text.strip() if result.success else ""
    if not content:
        # Deterministic fallback from facts — never invent numbers.
        sections = facts.get("sections") or {}
        lines = ["Daily business brief (deterministic fallback — AI unavailable).", ""]
        for key, value in sections.items():
            lines.append(f"## {key}")
            lines.append(json.dumps(value, ensure_ascii=False, default=str))
            lines.append("")
        lines.append("Advisory: review connected-system figures before acting.")
        content = "\n".join(lines)
    return {
        "ai_available": bool(result.success),
        "content": content,
        "prompt_version": prompt_version,
        "telemetry_id": telemetry_id,
        "provider": result.provider,
        "model": result.model,
        "error_code": result.error_code,
        "advisory": "Briefs are advisory. Figures come from connectors; confirm in MitraBooks before acting.",
    }
