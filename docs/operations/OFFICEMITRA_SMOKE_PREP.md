# OfficeMitra — Local Smoke Prep (Phases 4–6 + ADR-012)

**Purpose:** Local gates before staging browser/API smoke. Demo-tenant only for mutations.  
**Not authorization for ADR-010 companion writes.**

**Architecture under test (implemented only):**

```text
Phase 5  → Standalone Shell
Phase 4  → Writeback (ADR-008)
Phase 6  → Workflows (ADR-009)
ADR-012  → Policy Engine
```

ADR-010 companion write-back remains **Proposed / disabled**. Do not enable or attempt companion-product writes during this smoke.

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

Enable explicitly (parent `office_ai` alone is **not** enough for write/workflow paths):

| Flag | Needed for |
| --- | --- |
| `office_ai` | Module + ping |
| `office_ai.writeback` | Proposals / confirm / approve |
| `office_ai.workflows` | Templates / runs |

```text
office_ai enabled  ≠  writeback enabled  ≠  workflows enabled
```

App keys: `officemitra` (standalone) and/or `mitrabooks` (ERP shell).

## 2. Staging / demo smoke order

**API (staging):** `https://sanmitra-unified-next-staging-sg.onrender.com`  
**ERP UI:** `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`  
**Standalone UI (after Vercel deploy):** `/officemitra/` host or path per `frontend/vercel.json`

Confirm Render/Vercel picked up `main` at `5534909f` (or later) before signing off Phase 6 / policy boxes.

1. [Phase 5 standalone shell](OFFICEMITRA_PHASE5_STANDALONE_SHELL_SMOKE_CHECKLIST.md) — login + workspace loads  
2. **Action Registry + Capability Descriptors** (this doc §3.A–B) — before writeback/workflow mutations  
3. [Phase 4 write-back](OFFICEMITRA_PHASE4_WRITEBACK_SMOKE_CHECKLIST.md) — generate → confirm / dismiss  
4. [Phase 6 workflows](OFFICEMITRA_PHASE6_WORKFLOW_SMOKE_CHECKLIST.md) — template → run → idempotency → stop-on-failure + diagnostics  
5. [Policy engine ADR-012](OFFICEMITRA_POLICY_ENGINE_SMOKE_CHECKLIST.md) — evaluate + **negative** cases  

**Demo tenant enable (Platform Owner → Entitlements):**

```text
office_ai
office_ai.writeback
office_ai.workflows
```

(plus existing tasks/email/brief/calendar/meeting_notes/notifications as needed)

## 3. Quick API probes

### 3.A Action Registry health (ADR-008)

```http
GET /api/v1/officemitra/ping
GET /api/v1/officemitra/actions
```

When `writeback` or `workflows` is on, expect at least:

```json
{
  "registered_actions": ["create_notification", "create_task"]
}
```

(`update_task` is **not** a Phase 4–6 registered action unless explicitly added later.)

Also acceptable via ping: same `registered_actions` list when flags are on; empty list when both opt-in flags are off.

### 3.B Capability Descriptor (Registry → Descriptor → Policy)

```http
GET /api/v1/officemitra/actions/create_task
```

Expect (shape):

```json
{
  "action_type": "create_task",
  "requires_confirmation": true,
  "requires_maker_checker": false,
  "risk_level": "LOW"
}
```

Also check ping `action_descriptors[]` includes matching `capabilities` for each registered action.

### 3.C Policy Engine — happy path + negatives (ADR-012)

```http
POST /api/v1/officemitra/policy/evaluate
```

Body shape uses `action_type`, `intent`, optional `required_feature`, `maker_id`, `checker_id`, `allow_self_approval`, `approval_expiry_hours`.

| Case | Setup | Expect |
| --- | --- | --- |
| Confirm ready | writeback on, `create_task`, `intent=propose` or `confirm` | `allowed: true`, `execution_mode: confirmation` (or maker_checker if HIGH) |
| Flag disabled | writeback **off**, `required_feature=writeback`, `intent=confirm` | `allowed: false`, `decision: DENY`, `rule_id: POL-002` |
| Maker = checker | HIGH / `requires_maker_checker` action, `intent=approve`, same actor as maker, `allow_self_approval=false` | `allowed: false`, `rule_id: POL-021` |
| Expired approval | `approval_expires_at` in the past on evaluate/confirm path | `DENY` / `POL-020` (or proposal status `expired`) |

Decision payload must include: `allowed`, `execution_mode`, `decision`, `rule_id`, `reason` (and `approval_expiry_hours` when relevant).

### 3.D Workflows + mandatory diagnostics (ADR-009)

```http
GET  /api/v1/officemitra/proposals?status=open
GET  /api/v1/officemitra/workflows/templates
GET  /api/v1/officemitra/workflows/runs
POST /api/v1/officemitra/workflows/runs
```

After a run completes (applied or failed), **each** `step_results[]` entry must persist:

```json
{
  "duration_ms": 0,
  "retry_count": 0,
  "executor_version": "officemitra-executor-v1"
}
```

A successful workflow **without** these fields fails smoke (diagnostics are mandatory under ADR-009).

Expect on ping when flags are on: `writeback_enabled`, `workflows_enabled`, `policy_engine: true`.

## 4. Exit criteria — Smoke Prep Complete

Local foundation signoff record: [OFFICEMITRA_FOUNDATION_SMOKE_SIGNOFF.md](OFFICEMITRA_FOUNDATION_SMOKE_SIGNOFF.md)

- [ ] Local pytest suite green (§0)  
- [ ] Demo tenant configured with explicit flags (§1)  
- [ ] Standalone shell accessible (Phase 5 checklist)  
- [ ] Action Registry loaded expected actions (`create_task`, `create_notification`)  
- [ ] Capability Descriptors visible for `create_task` (confirmation + risk_level)  
- [ ] Policy Engine responding with structured outcomes  
- [ ] Policy negatives verified: flag off → DENY; maker=checker → DENY; expired → DENY/`expired`  
- [ ] Workflow diagnostics persisted (`duration_ms`, `retry_count`, `executor_version`)  
- [ ] Phase 4 / 5 / 6 / policy checklists prepared for operator signoff (boxes unchecked until staging run)  
- [ ] No ADR-010 companion writes enabled or attempted  

## 5. Non-goals / hard boundary

- Do **not** treat “implemented in docs” as “authorized in production.”  
- Do **not** post journals, invoices, GST, legal notices, or housing/temple mutations from OfficeMitra.  
- Companion connector writes wait for Accepted **ADR-010** + explicit allowlist.
