# OfficeMitra AI — Phase 1 (MVP) Smoke Checklist

**Product:** OfficeMitra AI  
**Phase:** 1 / MVP (Tasks + Email Summary + Daily Brief)  
**Date:** 2026-08-05  
**ADRs:** ADR-001 … ADR-007  

## Enable a demo tenant

1. Ensure the tenant has `app_key` `mitrabooks` (ERP host) **or** `officemitra` (standalone).
2. Add to `enabled_modules` (minimum):

```text
office_ai
```

Optional granular flags (omit one to disable that feature only):

```text
office_ai.tasks
office_ai.email
office_ai.brief
```

3. Optional AI: set `ANTHROPIC_API_KEY` (and `OFFICEMITRA_AI_*` if needed). Without a key, AI soft-fails; briefs still save a deterministic fallback.
4. Optional retention: `OFFICEMITRA_RETENTION_DAYS` (default 90) or tenant field `office_ai_retention_days`.

## API smoke

With auth + `X-App-Key`:

- [ ] `GET /api/v1/officemitra/ping` → `ok: true`, lists connectors
- [ ] `POST /api/v1/officemitra/tasks` → create manual task
- [ ] `POST /api/v1/officemitra/tasks/generate` → AI or soft-fail; `source=ai` when persisted
- [ ] `POST /api/v1/officemitra/emails/summarize` → summary (+ optional tasks)
- [ ] `POST /api/v1/officemitra/briefs/generate` → brief with `deployment_mode` `standalone` or `integrated`
- [ ] `GET /api/v1/officemitra/briefs/today` → latest generation
- [ ] Disable `office_ai.email` only → email routes 403; tasks still work

## UI smoke (MitraBooks shell)

- [ ] Nav → **OfficeMitra AI**
- [ ] Tasks tab: create / generate / mark done
- [ ] Email tab: paste + summarize
- [ ] Today Brief: generate; shows advisory disclaimer
- [ ] Module disabled on tenant → API 403 (menu may still show; API is source of truth)

## Isolation / safety

- [ ] Tenant A cannot read Tenant B tasks/emails/briefs
- [ ] No journal / invoice write paths from OfficeMitra
- [ ] Standalone tenant (only `office_ai`) generates brief without MitraBooks errors

## Exit criteria (Phase 1)

- [ ] Three features usable on a demo tenant
- [ ] Connector Manager skips missing modules quietly
- [ ] ADR-001…007 respected; InvestMitra untouched
- [ ] `pytest tests/test_office_ai*.py` green locally
