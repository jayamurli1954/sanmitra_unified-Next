# LegalMitra Stage 3 — Matter & Client Intelligence

**Document type:** Implementation specification  
**Product:** LegalMitra  
**Status:** Active implementation target  
**Version:** 1.1  
**Date:** 2026-08-02  
**Companion PRD:** [`docs/prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md`](../prd/LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md)

This document is the engineering contract for **Stage 3 (Matter & Client Intelligence)**.  
It incorporates the approved implementation plan plus review additions (status lifecycle, matter numbers, client–engagement model, timeline, structured briefs, dashboard widgets, reserved fields, and exit checklist).

---

## 1. Current vs target vs gap

| Layer | Current state | Target (Stage 3) | Gap |
| --- | --- | --- | --- |
| Clients | Tenant-scoped Client CRUD in MongoDB + tracker create form | Same | Harden empty-state UX; optional soft-archive parity |
| Matters | Lifecycle + auto numbers + tracker create form | Same | Matter status editor in UI (create supports draft/active/pending) |
| Documents | Matter-attached metadata + register UI | Same | Binary storage deferred |
| Timeline | Append-only API + auto events | Tracker chronology UI | Optional timeline panel |
| Intelligence | Structured Matter Intelligence Brief API + tracker brief panel | Same | Hybrid research into brief deferred |
| Tracker UI | Live dashboard when authenticated; preview only when signed out | Persona-filtered live board | Done for Stage 3 exit path |
| Stage 4 | Morning Brief / alerts (flagged) | — | **Deferred** from Stage 3 exit |

**Non-goals (Stage 3):** Full Legalit-style practice OS, cause-list sync, fee posting to MitraBooks, agentic multi-step workflows, production Claude enablement by default.

---

## 2. Data model (MongoDB)

All practice collections are scoped by `tenant_id` + `app_key` (`legalmitra`).  
Never trust `tenant_id` from the request body.

### 2.1 Client

One client may have many engagements (litigation, GST advisory, IT notice, secretarial, contract review).

| Field | Notes |
| --- | --- |
| `client_id` | UUID |
| `tenant_id`, `app_key` | Isolation |
| `display_name`, `client_type` | individual / organization |
| `email`, `phone`, `pan`, `gstin`, `address` | Optional contact/KYC |
| `notes`, `status` | active / archived |
| `created_by`, `created_at`, `updated_at` | Audit metadata |

### 2.2 Matter (engagement)

| Field | Notes |
| --- | --- |
| `matter_id` | UUID (internal) |
| `matter_number` | Backend-generated unique display id (e.g. `LM-2026-000001`, `GST-2026-000034`) |
| `client_id` | Required FK to client |
| `title`, `matter_type`, `status` | See lifecycle below |
| `jurisdiction`, `description` | Optional |
| Reserved (optional now): `assigned_users`, `tags`, `priority`, `practice_area`, `court`, `opposite_party`, `billing_reference` | Future-proof without Stage 4/5 features |
| Soft-archive | Prefer `status=archived` + `archived_at` |

### 2.3 Matter status lifecycle

| Status | Purpose |
| --- | --- |
| `draft` | Newly created |
| `active` | Currently being worked on |
| `pending` | Waiting for external action |
| `on_hold` | Temporarily paused |
| `closed` | Completed |
| `archived` | Read-only historical record |

Transitions are validated server-side. Arbitrary free-text statuses are rejected.

### 2.4 Documents / timeline / briefs

- **Documents:** metadata only in Stage 3 (`document_id`, `matter_id`, `filename`, `doc_type`, `notes`, review flags). Binary storage may reuse existing upload paths later.
- **Timeline:** append-only chronological events (`event_type`, `summary`, `actor_id`, `occurred_at`, optional `payload`).
- **Briefs:** structured advisory object with sources, limitations, confidence, `human_review_required=true`.

### 2.5 Matter brief structure (fixed)

```text
Matter Overview
Key Facts
Applicable Law
Important Dates
Documents Reviewed
Current Status
Risks
Suggested Next Actions
Limitations
Confidence
Human Review Required
```

Briefs are grounded summaries from matter/client/document/timeline data (and optionally hybrid research). They are **not** final legal advice.

---

## 3. API surface (under `/api/v1/legal`)

| Method | Path | Purpose |
| --- | --- | --- |
| CRUD | `/clients`, `/clients/{id}` | Client management |
| CRUD | `/matters`, `/matters/{id}` | Matter management |
| POST/GET | `/matters/{id}/documents` | Attach / list documents |
| GET/POST | `/matters/{id}/timeline` | List / add timeline events |
| POST/GET | `/matters/{id}/brief` | Generate / fetch latest brief |
| GET | `/practice/dashboard` | Live widgets |

Module gate: `require_enabled_module("legal")`.  
Legacy `POST/GET /legal/cases` remains for compatibility; new practice UIs use clients/matters.

---

## 4. Dashboard widgets (Stage 3)

Replace placeholder tracker metrics with live aggregates where authenticated:

- Active Matters  
- Upcoming Hearings (from timeline / matter important dates)  
- Upcoming Compliance Deadlines  
- Recently Added Clients  
- Matters Awaiting Review (`pending` / brief needing review)  
- AI Matter Briefs (recent)  
- Recent Documents  

Fee ledger is implemented in Stage 6 (live summary on tracker when billing is enabled).

---

## 5. Security and AI rules

- Tenant + app isolation on every read/write.  
- Audit every create/update/status change/document attach/brief generate.  
- Soft-archive preferred over hard delete.  
- Briefs always set `human_review_required` and advisory limitations.  
- Do not send confidential matter documents to external providers unless tenant policy and user authorization allow it (reuse Stage 2 provider gates).  
- Persona adaptation is presentation-only; authorization remains RBAC/module checks.

---

## 6. Acceptance criteria (Stage 3 exit)

Stage 3 is complete only if:

- [x] Client CRUD works  
- [x] Matter CRUD works (lifecycle + auto matter numbers)  
- [x] Tenant isolation verified  
- [x] Matter documents attached successfully  
- [x] Matter Brief generated from real matter data (structured sections)  
- [x] Dashboard displays live matter/client information when authenticated  
- [x] Audit logging verified  
- [x] All Stage 2 LegalMitra tests continue to pass  

**Frontend hardening (2026-08-16):** Tracker signed-in path uses API-only practice SoR (no demo/localStorage fallback), client/matter create forms, Matter Intelligence Brief panel, persona-filtered live board, and HTTP Stage 3 route tests (`tests/test_legalmitra_stage3_http.py`).

---

## 7. Implementation sequence

1. Schemas + indexes + counters for matter numbers  
2. Client service/router + tests  
3. Matter service/router + lifecycle + timeline auto-events + tests  
4. Documents + brief generation + dashboard  
5. Tracker frontend live wiring (fallback to preview banner when unauthenticated)  
6. Preflight + Stage 2 regression  

---

## 8. Document control

| Version | Date | Note |
| --- | --- | --- |
| 1.0 | 2026-08-02 | Initial Stage 3 implementation plan |
| 1.1 | 2026-08-02 | Review additions: lifecycle, matter numbers, multi-engagement clients, timeline, structured briefs, widgets, reserved fields, exit checklist |
