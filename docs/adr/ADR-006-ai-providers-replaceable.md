# ADR-006: AI providers are replaceable

**Status:** Accepted  
**Date:** 2026-08-05  
**Product scope:** OfficeMitra AI  

## Context

AI models and vendors change quickly. Hard-coding Anthropic/Claude (or any single vendor) into OfficeMitra services would force widespread refactors when switching models, adding OpenAI/Gemini, or running a local LLM for demos/offline.

## Decision

OfficeMitra AI calls models only through a **provider interface**:

```text
orchestrator / services
        ↓
  AIProvider Protocol
        ↓
 Claude | OpenAI | Gemini | Local | Null (safe fallback)
```

- Application code depends on `complete(prompt, …) -> ProviderResult`, not vendor SDKs.
- Provider selection is configuration-driven (`OFFICEMITRA_AI_PROVIDER`, keys, model names).
- Missing keys or failures return a structured soft-fail (`ai_available=false`), never invented business numbers.
- Every completion records telemetry: provider, model, tokens_in/out, latency_ms, estimated_cost, success, `tenant_id`, `prompt_version`.

## Consequences

- New providers are adapters under `app/modules/office_ai/ai/providers/`.
- Prompt files are versioned (`*_v1.txt`) and `prompt_version` is stored on Mongo outputs.
- Tests can inject a fake provider without network calls.
