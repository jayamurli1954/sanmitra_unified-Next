# OfficeMitra — Staff missing-document requests (ADR-017) implementation plan

**Document type:** Implementation plan (for Antigravity / architecture review)  
**Product:** OfficeMitra AI — Documents package follow-on  
**Status:** Approved with changes (Antigravity 2026-09-12); implementing  
**Version:** 1.1  
**Date:** 2026-09-12  
**ADR:** [ADR-017](../adr/ADR-017-officemitra-missing-document-requests.md) (Accepted)  
**PRD:** [OFFICEMITRA_DOCUMENTS_PACKAGE.md](../prd/OFFICEMITRA_DOCUMENTS_PACKAGE.md) v1.1  
**Depends on:** [ADR-016](../adr/ADR-016-officemitra-documents-package.md) Documents (on `origin/main`), [ADR-008](../adr/ADR-008-officemitra-confirmed-writeback.md) OfficeMitra-owned tasks, [ADR-015](../adr/ADR-015-officemitra-review-workspaces.md) Review notes  
**Does not supersede:** ADR-016, [ADR-010](../adr/ADR-010-officemitra-companion-writeback.md) (still Proposed), LegalMitra notices

This plan is the contract for the next OfficeMitra slice. It is **not** a new Mitra brand.

---

## 0. Reviewer brief (Antigravity)

Please review this plan **before** any further implementation or commit.

Approve or reject each locked decision in §1. Flag any gap that would:

- post journals or mutate the live MitraBooks PostgreSQL ledger
- query `business_ca_document_metadata` from OfficeMitra code (ADR-003)
- write CA queue rows / status / uploads from OfficeMitra (needs Accepted ADR-010)
- email or WhatsApp the client
- add a client portal
- add a new Mitra brand
- grow `frontend/shared/office-ai-workspace.js` past **1253** lines (`scripts/file_size_baseline.json`)

Return: **Approve**, **Approve with changes**, or **Reject**, plus numbered comments against §15.

---

## 1. Locked decisions (product owner)

| # | Decision | Locked value |
| --- | --- | --- |
| D1 | Brands | No ClientMitra / DocumentsMitra / ReviewMitra / PracticeOS. Packages stay inside OfficeMitra. |
| D2 | Slice | Staff missing-document **requests** only. Not a client portal. |
| D3 | Flag | `office_ai.documents.requests` default **off**. Requires parent `office_ai.documents`. Parent Documents / Review do not enable it. |
| D4 | Gap report | Deterministic compare of a **fixed India staff checklist** to CA queue `document_type` for the engagement book. No LLM. |
| D5 | Request action | Create an OfficeMitra **task** (Mongo `officemitra_tasks`). Optional Review note if `office_ai.review.notes` is on. |
| D6 | Idempotency | One **open** task per tenant + engagement + `document_type`. Repeat POST returns the existing task (`created: false`). |
| D7 | Writes allowed | OfficeMitra-owned Mongo only (task, optional note, in-app notification). |
| D8 | Writes forbidden | CA queue insert/update/status, file upload, SMTP/WhatsApp, PostgreSQL journals, GST/invoice/payroll. |
| D9 | Connector | Reuse ADR-016 MitraBooks connector (`list_ca_staff_documents`). No new collection access. |
| D10 | Enablement | `demo-mfg-mis` only. Refuse `demo-mitrabooks-business` and production ERP tenants. |
| D11 | UI file | All new Documents UI in `frontend/shared/office-ai-documents.js`. Re-export via `office-ai-review.js`. Do not add import lines or logic to `office-ai-workspace.js`. |
| D12 | Router file | New routes stay in `app/modules/office_ai/documents_router.py`. Do not grow `office_ai/router.py` except existing ping import. |

**Do not reopen D1–D2, D7–D8, D10–D12 without a superseding ADR.**

---

## 2. Current state (baseline)

Honest inventory. Do not describe ADR-017 as shipping.

| Area | Exists today? | Notes |
| --- | --- | --- |
| Documents tab + CA queue list | Yes (ADR-016 on `origin/main`) | `GET /api/v1/officemitra/documents/queue` via connector |
| Review note ↔ `ca_document_id` | Yes | OfficeMitra Mongo only |
| Flag `office_ai.documents` | Yes | Default off; parent `office_ai` / Review do not enable it |
| Connector `list_ca_staff_documents` / `get_ca_staff_document` | Yes | Calls `ca_clients.*`; `CA_QUEUE_APP_KEY = "mitrabooks"` |
| Fail-soft without `business` | Yes | `enabled: false`, `reason: business_module_off` |
| Gap report vs India checklist | **No** (planned) | Staff still eyeball the queue |
| Staff request → OfficeMitra task | **No** (planned) | |
| Client portal / client email | No | Explicitly deferred |
| Companion CA writes | No | ADR-010 still Proposed |
| `frontend/shared/office-ai-workspace.js` | 1253 / 1253 | Grandfathered ceiling; must not grow |
| Demo seed | Yes | `scripts/seed_documents_demo.py` locked to `demo-mfg-mis`; seeds one `bank_statement` |

### Working-tree warning

A **draft** ADR-017 attempt may exist in the local working tree (registry helper, service stubs, routes, UI). Treat it as **unsigned**. After this plan is approved, implement against **this document**, not against leftover draft code. Discard or rewrite any draft that contradicts §1 / §6 / §8.

---

## 3. Target state (this slice only)

An accountant on `demo-mfg-mis` with `office_ai.documents` **and** `office_ai.documents.requests`:

1. Opens the existing Documents tab.
2. Sees a **gap table**: five expected types, Present / Missing against the CA queue for the selected engagement book (`accounting_entity_id`, default `primary`). When an engagement is selected **and** it has a `period`, only queue rows with that period count as Present.
3. Clicks **Request** on a missing type.
4. Gets an open OfficeMitra task titled like `Missing document: GST returns working`.
5. If Review notes are enabled **and** an engagement is selected, also gets a Review note pointing at that same task id (one task, not two).
6. Repeat Request for the same type while the task is open returns the existing task; no second task.
7. UI copy states: upload stays in MitraBooks CA Practice (`ca-access`); **no client email** was sent.

If `office_ai.documents` is on but `office_ai.documents.requests` is off: queue/link still work; gap/request routes return **403**.

If `business` is off: gap report fail-softs like the queue (all checklist rows Missing or queue `enabled: false`); creating a staff task is still allowed (staff still need the paper). Task notes state that CA Practice is not active.

---

## 4. Gap (must be built after plan approval)

- Registry helper `is_office_ai_documents_requests_enabled` (parent Documents required), nested-dot pattern matching `office_ai.review.notes`.
- `GET /api/v1/officemitra/documents/gaps`
- `POST /api/v1/officemitra/documents/requests`
- Ping: `documents_capabilities.requests`, `adr_017`
- Service: checklist + gap_report + create_staff_request
- Task fields: `kind=missing_document`, `document_type`, `engagement_id`
- Optional Review note via `review_store.create_note(..., task_id=...)` — **not** `create_note_with_task` (that helper creates a **second** task)
- In-app notification only (`kind=missing_document_request`); add to `NOTIFICATION_KINDS`
- UI gap table + Request button in `office-ai-documents.js` only
- Tests, seed flag + smoke, docs listed in §12
- `graphify update .` after code; targeted pytest; file-size guard

---

## 5. Non-goals (explicit)

| Item | Why out |
| --- | --- |
| Client self-portal | Later package; MitraBooks already has a CA invite viewer |
| Client email / WhatsApp / SMTP | Outreach is a different product; companion-adjacent |
| OfficeMitra upload / CA status / classify | Companion write; needs Accepted ADR-010 |
| AI / LLM gap detection | Checklist must stay deterministic |
| New expected types beyond the five | Checklist change in a follow-up; not this PR |
| Period-level matching of queue rows | **Locked by review:** when `engagement_id` resolves to a period, filter queue rows to that period; otherwise book-scoped |
| LegalMitra knowledge / notices / compliance calendar | Stay on LegalMitra unless a later ADR composes them |
| Advisory, timesheets, analytics | Later OfficeMitra packages |
| Enabling `demo-mitrabooks-business` | Live ERP demo must stay off |

---

## 6. Flag and access design

### 6.1 Nested flag (same as Review notes)

Do **not** add `documents.requests` to `ModuleDefinition.features`. `require_module_feature("office_ai", "documents.requests")` will fail (`Unknown feature`) because registry features are single-segment (`documents`, `review`, `mis`).

Pattern already used for `office_ai.review.notes`:

1. Route depends on `require_enabled_module_feature("office_ai", "documents")`.
2. Extra check `is_office_ai_documents_requests_enabled(...)` → HTTP 403 `Enable office_ai.documents.requests`.

Helper:

```text
office_ai in enabled_modules
AND office_ai.documents enabled (existing opt-in helper)
AND (
      "office_ai.documents.requests" in enabled_modules
   OR office_ai_features contains "requests" or "documents.requests"
)
```

Parent Documents **without** the nested flag must return False.

### 6.2 Tenant context

`tenant_id` from trusted auth context only. Never from request body. Module + feature gates before any queue read or task insert.

---

## 7. Checklist (v1, India staff)

Fixed tuple in `documents_service.py`. Case-insensitive exact match on CA queue `document_type`.

| Code | Label |
| --- | --- |
| `bank_statement` | Bank statement |
| `gst_returns` | GST returns working |
| `tds_challans` | TDS challans |
| `trial_balance` | Trial balance |
| `receivable_ageing` | AR ageing |

MitraBooks CA `document_type` is a free-text string (max 80). Demo seed already uses `bank_statement`. Unknown POST types → 400.

**Present** = any queue row for that book whose `document_type` lowercases to the code. Do not invent aliases (`Bank Statement`, `GST`) in v1 unless Antigravity requires them (§15 Q2).

---

## 8. API contract

Base: `/api/v1/officemitra` (existing documents router). All routes tenant-scoped.

| Method | Path | Gate | Behavior |
| --- | --- | --- | --- |
| GET | `/documents/status` | `office_ai` | Ping fields including `documents_capabilities.requests` |
| GET | `/documents/queue` | `office_ai.documents` | Unchanged (ADR-016) |
| POST | `/documents/notes/{note_id}/link` | documents + review.notes | Unchanged |
| POST | `/documents/notes/{note_id}/unlink` | documents + review.notes | Unchanged |
| GET | `/documents/gaps` | documents **+** documents.requests | Gap report |
| POST | `/documents/requests` | documents **+** documents.requests | Create or reuse staff task |

### GET `/documents/gaps`

Query: `engagement_id?`, `accounting_entity_id?` (same as queue).

Response (shape):

```json
{
  "enabled": true,
  "reason": null,
  "error": null,
  "source": "mitrabooks.list_ca_document_metadata",
  "accounting_entity_id": "primary",
  "items": [
    { "document_type": "bank_statement", "label": "Bank statement", "present": true },
    { "document_type": "gst_returns", "label": "GST returns working", "present": false }
  ],
  "missing": [{ "document_type": "gst_returns", "label": "GST returns working", "present": false }],
  "missing_count": 1,
  "client_portal": false,
  "client_email": false,
  "adr_017": "accepted"
}
```

404 if `engagement_id` is supplied but not found for this tenant.

### POST `/documents/requests`

Body (`DocumentsMissingRequest`):

```json
{
  "document_type": "gst_returns",
  "engagement_id": "<optional>",
  "accounting_entity_id": "<optional>"
}
```

| Case | HTTP | Body |
| --- | --- | --- |
| Created | 200 | `{ "item": <task>, "created": true, "note": <note or null>, "client_email": false }` |
| Idempotent hit | 200 | `{ "item": <existing open task>, "created": false, "note": null, "client_email": false }` |
| Type already on queue | 400 | already on the CA queue |
| Unknown type | 400 | unknown expected document type |
| Engagement missing | 404 | |
| Flag off | 403 | Enable `office_ai.documents.requests` |

Task fields to persist:

- `kind`: `missing_document`
- `document_type`: checklist code (lowercase)
- `engagement_id`: string or null
- `source`: `manual` (not `ai`)
- `title`: `Missing document: {label}` plus ` ({period})` when engagement has a period
- `notes`: instruct staff to upload in MitraBooks CA Practice; do not email the client from OfficeMitra

In-app notification: `kind=missing_document_request`, dedupe key `missing_doc:{tenant_id}:{engagement_id or none}:{code}`. No SMTP.

---

## 9. Service rules

1. Gap report **must** call existing `list_queue` → connector. OfficeMitra must not import `CA_DOCUMENTS_COLLECTION` or query `business_ca_document_metadata`.
2. Optional note: `review_store.create_note(..., task_id=task["id"])`. **Forbidden:** `review_service.create_note_with_task` (creates a duplicate task).
3. Idempotency lookup: open task with `tenant_id` + `kind=missing_document` + `document_type` + `engagement_id` (null-safe). Tenant-scoped Mongo only.
4. No `post_journal`, no `app.accounting` imports in documents service/router.
5. `client_email` / `client_portal` always false in responses.

---

## 10. UI (Documents tab only)

File: `frontend/shared/office-ai-documents.js`

- State: `documentsRequestsEnabled`, `documentsGaps` (plus existing queue state).
- `applyDocumentsPing`: set `documentsRequestsEnabled` from `payload.documents_capabilities.requests`.
- `refreshDocumentsData`: if requests enabled, also GET `/documents/gaps` with the same `engagement_id` as the queue.
- Panel: gap table under the queue. Missing rows get `data-office-ai-action="documents-request"` + `data-document-type`.
- Copy: “Raises an OfficeMitra task. Does not email the client or write the CA queue.”
- If requests flag off: muted line “Enable `office_ai.documents.requests`…”, no Request buttons.

`office-ai-review.js`: re-export Documents helpers (already does). Spread `DOCUMENTS_STATE_DEFAULTS` into `REVIEW_STATE_DEFAULTS` so workspace state picks up new keys **without** editing `office-ai-workspace.js`.

`office-ai-workspace.js`: **no new lines**. Ceiling 1253. Existing tab insert / `handleDocumentsAction` / `refreshDocumentsData` already dispatch into the Documents module.

---

## 11. Tests (`tests/test_office_ai_documents.py`)

Add to the existing ADR-016 file (do not start a new brand-named test module).

| Test | Assert |
| --- | --- |
| Nested flag | Parent Documents alone does **not** enable requests. Nested flag without parent Documents is False. Both True. |
| Gap present/missing | Queue with `bank_statement` → that row `present: true`; `gst_returns` `present: false`. |
| Idempotent request | Two `create_staff_request` for same missing type + engagement → same task id, second `created: false`. |
| Reject present type | Request `bank_statement` when on queue → `DocumentsError`. |
| Tenant isolation | Task/note for tenant A not visible as tenant B. |
| No ledger / no CA collection | `inspect.getsource` on documents service + router: no `post_journal`, `app.accounting`, `business_ca_document_metadata`, `CA_DOCUMENTS_COLLECTION`, `smtplib`. |
| UI strings | Combined workspace + documents JS: `/documents/gaps`, `documents-request`, `office_ai.documents.requests`, “does not email the client”. |
| Seed lock | Unchanged: refuse `demo-mitrabooks-business`. |
| Route contract | Add GET `/api/v1/officemitra/documents/gaps` and POST `/api/v1/officemitra/documents/requests` to `tests/test_core_route_contract_safety.py`. |

---

## 12. Seed, smoke, docs (after code)

**Seed** `scripts/seed_documents_demo.py`:

- Also enable `office_ai.documents.requests`.
- `--run-smoke`: keep existing `bank_statement` + note link; then `gap_report` and `create_staff_request` for a **missing** type (e.g. `gst_returns`). Print `created` / task id. Still no journals, no CA status mutation, no SMTP.

**Smoke checklist** `docs/operations/OFFICEMITRA_DOCUMENTS_SMOKE_CHECKLIST.md`:

- Add ADR-017 lifecycle: gaps → Request → task → repeat Request is idempotent → still no client email.
- Move “missing-doc requests” out of Non-goals; keep client email / portal / classify as non-goals.

**Policy / architecture (same PR as code, not this plan-only file):**

- `docs/adr/README.md` index row ADR-017
- `AGENTS.md` §13a (current/target/deferred + Documents requests bullet) + version history 1.10
- `docs/architecture/MODULE_REGISTRY.md` `office_ai` row
- `docs/architecture/CURRENT_VS_TARGET.md` OfficeMitra row
- `docs/architecture/OFFICEMITRA_AI_IMPLEMENTATION_PLAN.md` Phase **7d**, locked D19, history 1.8
- Documents PRD: mark ADR-017 gap items done; remaining = operator signoff on `demo-mfg-mis`
- Review PRD deferred row: staff requests are ADR-017; client emails still deferred

---

## 13. Implementation sequence (after Approve)

1. Registry helper + tests for flag parent requirement.
2. Task service: optional `kind` / `document_type` / `engagement_id` + `find_open_missing_document_task`.
3. Documents service: checklist, `gap_report`, `create_staff_request`.
4. Schema + router GET/POST + ping fields.
5. UI in `office-ai-documents.js` + `DOCUMENTS_STATE_DEFAULTS` spread in review JS.
6. Tests + route contract.
7. Seed + smoke checklist.
8. Policy docs listed in §12.
9. `graphify update .`
10. Targeted pytest: `tests/test_office_ai_documents.py`, `tests/test_core_route_contract_safety.py`, plus any registry tests that cover nested flags.
11. `python scripts/preflight.py` before commit/push (venv `D:\sanmitra_unified-Next\.venv`). Confirm `office-ai-workspace.js` still 1253 lines.

Do not start client portal, advisory, or ADR-010 writes in the same PR.

---

## 14. Risks

| Risk | Mitigation |
| --- | --- |
| Duplicate tasks if optional note uses `create_note_with_task` | Use `review_store.create_note` with existing `task_id` |
| Nested flag treated as a registry module (`is_module_feature_flag` rejects extra dots) | Same as `office_ai.review.notes`; helper checks the full dotted string in `enabled_modules` |
| Growing `office-ai-workspace.js` | All UI in documents JS; file-size baseline 1253 |
| Accidental CA / ledger writes | Source-inspection tests + connector-only reads |
| Matching free-text CA types | v1 exact lowercase code; demo seed already uses `bank_statement` |
| Enabling live ERP demo | Seed assert continues to refuse `demo-mitrabooks-business` |

Rollback: flags default off. Disable `office_ai.documents.requests` on the demo tenant. No ledger reversal needed (no journals). Open staff tasks can be cancelled in OfficeMitra.

---

## 15. Antigravity review questions

Please answer each:

1. **Approve D1–D12?** Any decision that should be Proposed-only until a later ADR?
2. **Checklist matching:** exact lowercase `document_type` codes only, or also aliases / labels?
3. **Period:** book-scoped (`accounting_entity_id` only) vs also require queue `period` == engagement `period`?
4. **Standalone without `business`:** allow creating a staff task when the queue fail-softs, or 400 because there is no CA book?
5. **Optional Review note:** create note only when `office_ai.review.notes` **and** `engagement_id` present — correct?
6. **Notification:** in-app OfficeMitra inbox is enough (no email)? Confirm `missing_document_request` as a new `NOTIFICATION_KINDS` value.
7. **Phase label:** call this OfficeMitra plan Phase **7d** under Documents, not a new product phase?
8. **Working-tree draft:** discard and re-implement from this plan, or review the draft in place after Approve?

---

## 16. Acceptance (implementation PR, after this plan)

PR must state:

- Tenant isolation on task/note/gap reads and writes
- App-key / module / `office_ai.documents.requests` gates
- No accounting posts; no CA collection queries from OfficeMitra
- Current vs target vs deferred called out in docs
- `python scripts/preflight.py` passed
- `office-ai-workspace.js` still ≤ 1253 lines
- No blocked git/fs/db commands

---

## Document history

| Version | Date | Notes |
| --- | --- | --- |
| 1.0 | 2026-09-12 | First review draft for Antigravity; implementation not started as signed work |
| 1.1 | 2026-09-12 | Antigravity: Approve with changes. Locked: exact codes; period-match when engagement has period; fail-soft task without `business`; repair draft in place |
