# OfficeMitra — Local Smoke Prep (Phases 4–6 + ADR-012)

**Purpose:** Local gates before staging browser/API smoke. Demo-tenant only for mutations.  
**Not authorization for ADR-010 companion writes.**

## 0. Local automated gate (always)

From repo root:

```powershell
python -m pytest tests/test_office_ai_phase4_writeback.py tests/test_office_ai_phase6_workflows.py tests/test_office_ai_policy.py tests/test_officemitra_standalone_shell.py tests/test_office_ai.py tests/test_office_ai_phase2.py -q --tb=short
```

Optional broader gate before push:

```powershell
python scripts/preflight.py
```

(Add `--frontend` if you also changed `frontend/**` and are pushing.)

## 1. Demo tenant flags

Enable explicitly (parent `office_ai` alone is not enough for write/workflow paths):

| Flag | Needed for |
| --- | --- |
| `office_ai` | Module + ping |
| `office_ai.writeback` | Proposals / confirm / approve |
| `office_ai.workflows` | Templates / runs |

App keys: `officemitra` (standalone) and/or `mitrabooks` (ERP shell).

## 2. Staging / demo smoke order

1. [Phase 5 standalone shell](OFFICEMITRA_PHASE5_STANDALONE_SHELL_SMOKE_CHECKLIST.md) — login + workspace loads  
2. [Phase 4 write-back](OFFICEMITRA_PHASE4_WRITEBACK_SMOKE_CHECKLIST.md) — generate → confirm / dismiss  
3. [Phase 6 workflows](OFFICEMITRA_PHASE6_WORKFLOW_SMOKE_CHECKLIST.md) — template → run → idempotency → stop-on-failure  
4. [Policy engine ADR-012](OFFICEMITRA_POLICY_ENGINE_SMOKE_CHECKLIST.md) — `policy/evaluate`, maker≠checker, expiry  

## 3. Quick API probes

```http
GET  /api/v1/officemitra/ping
POST /api/v1/officemitra/policy/evaluate
GET  /api/v1/officemitra/proposals?status=open
GET  /api/v1/officemitra/workflows/templates
GET  /api/v1/officemitra/workflows/runs
```

Expect on ping when flags are on: `writeback_enabled`, `workflows_enabled`, `policy_engine: true`.

## 4. Exit criteria for “smoke prep done”

- [ ] Local pytest gate above is green  
- [ ] Demo tenant flags documented/set  
- [ ] Checklists 1–4 ready for operator signoff (boxes still unchecked until staging run)  
- [ ] No companion-product write attempts (ADR-010 still Proposed)
