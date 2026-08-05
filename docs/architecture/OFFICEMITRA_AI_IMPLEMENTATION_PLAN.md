# OfficeMitra AI — Detailed Implementation Plan

**Document type:** Implementation plan (architecture + delivery sequence)  
**Product:** OfficeMitra AI  
**Status:** Phase 1 (MVP) implemented locally — staging smoke pending  
**Version:** 1.3  
**Date:** 2026-08-05  
**ADRs:** [`docs/adr/`](../adr/README.md) ADR-001 … ADR-007  
**Smoke checklist:** [`docs/operations/OFFICEMITRA_PHASE1_SMOKE_CHECKLIST.md`](../operations/OFFICEMITRA_PHASE1_SMOKE_CHECKLIST.md)  
**Supersedes positioning in:** informal notes that framed OfficeMitra as the SanMitra “operating system”

> **Success criteria:** A single tenant can securely create tasks, summarize pasted emails into actionable tasks, and generate a daily brief from OfficeMitra-native data and *any available* connectors (including zero connectors in standalone mode), without any direct cross-product database access, while remaining fully compliant with ADR-001 through ADR-007.

---

## 0. Locked decisions

| # | Decision | Locked value | ADR |
| --- | --- | --- | --- |
| D1 | Platform role | MitraBooks ERP = transactional core; OfficeMitra = thin AI orchestration layer | ADR-001 |
| D2 | Cross-product access | Connectors → product service layers only | ADR-002 |
| D3 | Database | No cross-product DB reads/writes; OfficeMitra owns Mongo only; no new Postgres for MVP | ADR-003 |
| D4 | Tenancy | `tenant_id` only (no parallel `organization_id`) | ADR-004 |
| D5 | MVP write policy | Read-only toward other products; own collections writable | ADR-005 |
| D6 | API prefix | `/api/v1/officemitra/...` (module-prefixed, versioned — matches SanMitra route convention; avoids colliding with generic `/tasks`) | — |
| D7 | Module key | `office_ai` with sub-feature flags `office_ai.tasks`, `office_ai.email`, `office_ai.brief` | — |
| D8 | App keys | `officemitra` (standalone), plus `mitrabooks`, `legalmitra`, `gruhamitra`, `mandirmitra` when hosted in those shells — explicit list, not `*` | ADR-007 |
| D9 | MVP UI home | Module panel inside **MitraBooks ERP shell** when using `mitrabooks`; standalone shell is allowed for OfficeMitra-only clients (same APIs) | ADR-007 |
| D10 | Long-term UI | Optional dedicated OfficeMitra experience for non-ERP buyers — never the platform OS | ADR-001 / ADR-007 |
| D11 | InvestMitra | Explicitly out of unified OfficeMitra scope | AGENTS.md |
| D12 | Branding | `GruhaMitra` (never GharMitra/GrihaMitra); product display name **OfficeMitra AI** | — |
| D13 | AI providers | Replaceable via provider interface; never hard-wire vendors into services | ADR-006 |
| D14 | AI telemetry | Every completion stores provider/model/tokens/latency/cost/success/`prompt_version`/`tenant_id` | — |
| D15 | Prompt versioning | Versioned prompt files (`*_vN.txt`); `prompt_version` persisted on outputs | — |
| D16 | Modular deployment | No mandatory companion modules; Connector Manager discovers integrations at runtime | ADR-007 |

**Do not reopen D1–D5, D13, or D16 without a superseding ADR.**

---

## 1. Current state vs target state

### Current state (today)

| Area | Reality |
| --- | --- |
| OfficeMitra module | **Implemented** under `app/modules/office_ai/` with Phase 1 APIs + MitraBooks shell UI |
| Unified backend | FastAPI modular monolith with MitraBooks, LegalMitra, MandirMitra, GruhaMitra paths |
| Tenancy | Trusted `tenant_id`, `app_key` (incl. `officemitra`), `organization_type`, `enabled_modules` |
| Data stores | MongoDB domain + PostgreSQL accounting |
| Deployable frontends | MitraBooks Unified ERP + LegalMitra; OfficeMitra panel inside ERP shell |
| InvestMitra | Excluded from unified backend/deployment |

### Target state (after this plan’s MVP)

| Area | Target |
| --- | --- |
| Backend | `app/modules/office_ai/` (or `officemitra/`) with routers, services, connectors, AI helpers |
| Data | Tenant-scoped Mongo: `officemitra_tasks`, `officemitra_emails`, `officemitra_briefs` |
| APIs | Protected `/api/v1/officemitra/*` with module + RBAC checks |
| AI | Three plain Claude (or configured provider) functions: summarize email, generate tasks, build daily brief |
| Connectors | Real MitraBooks read connector; stub Legal/Mandir/Gruha returning `[]` |
| UI | “Office AI” workspace in MitraBooks shell: Tasks, Email Summary, Today (Brief) |
| Policy | AGENTS.md OfficeMitra section + ADRs + registry entry for `office_ai` |

### Gap (what must be built)

- Module registry entry, AGENTS.md section, route registration
- Mongo models/indexes, CRUD + AI endpoints, connector stubs + MitraBooks connector
- Provider config, prompt files, safe fallbacks, retention hooks
- MitraBooks shell navigation + three screens
- Tests: tenancy, module gate, connector isolation, AI fallback

### Deferred (explicit non-goals for MVP)

Multi-agent frameworks, vector DB / OfficeMitra-owned RAG, Gmail/Outlook/WhatsApp/Slack/Zoom, billing engine for OfficeMitra, marketplace, write-back automation into ERP/legal, InvestMitra connectors, Kubernetes, 180-page mega-PRD execution.

---

## 2. Positioning (canonical diagram)

```text
                    SanMitra Unified Backend
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
      MitraBooks ERP    GruhaMitra /      OfficeMitra AI
   (transactional core)  MandirMitra      (thin AI module)
            │                 │                 │
            └──────── service interfaces ───────┘
                      (Connector Manager)

LegalMitra ──────── connector contract (separate product frontend)
InvestMitra ─────── out of unified scope
```

### Deployment profiles (same codebase)

| Profile | Enabled modules (typical) | Brief sources |
| --- | --- | --- |
| **Standalone** | `office_ai` (+ auth/users/audit) | Tasks + emails only |
| **Business** | `office_ai` + business/accounting | + MitraBooks connector |
| **Housing** | `office_ai` + housing | + GruhaMitra connector |
| **Temple** | `office_ai` + temple | + MandirMitra connector |
| **Professional / Legal** | `office_ai` + legal (LegalMitra host) | + LegalMitra connector |
| **Enterprise** | Multiple of the above | All available connectors |

Profiles are **configuration**, not separate repositories.

### Daily Brief flow

```text
Tasks + Emails (always)
        ↓
Connector Manager → discover by enabled_modules
        ↓
  loaded connectors → merge facts
  none loaded     → continue (standalone)
        ↓
Generate brief (never invent missing ERP/legal numbers)
```

User flow for insights:

```text
User → OfficeMitra UI → OfficeMitra service → Connector Manager → Product service → JSON → AI brief/draft → User
```

---

## 3. Capability maturity model

| Phase | Name | Capability | Status in this plan |
| --- | --- | --- | --- |
| **0** | Foundation | ADRs, AGENTS.md, registry, scaffold, ping route, shell nav stub | **Done** |
| **1 / MVP** | Three features | Task Generator, Email Summary (paste), Daily Brief via Connector Manager (standalone-safe) | **Implemented locally** — use [`docs/operations/OFFICEMITRA_PHASE1_SMOKE_CHECKLIST.md`](../operations/OFFICEMITRA_PHASE1_SMOKE_CHECKLIST.md) for staging signoff |
| **2** | Productivity depth | Calendar hooks, meeting notes, in-app notifications | Post-MVP |
| **3** | Ecosystem read | Replace stub connectors for LegalMitra, GruhaMitra, MandirMitra | Weeks 6–8 stretch / Phase 3 |
| **4** | Approved automation | AI-proposed writes with **explicit user confirmation** + audit | Requires new ADR |
| **5** | Experience expansion | Optional standalone OfficeMitra UI for non-ERP tenants; third-party integrations | Optional |

**MVP ships Phase 0 + Phase 1 only.** Phases 2–5 are roadmap, not commitment inside the first PR series.

---

## 4. Architecture

### 4.1 Package layout (target)

```text
app/modules/office_ai/
  __init__.py
  router.py                 # /api/v1/officemitra
  schemas.py
  models.py                 # Mongo document helpers / collection names
  retention.py              # optional purge helpers aligned with tenant policy
  services/
    task_service.py
    email_service.py
    brief_service.py
  connectors/
    base.py                 # enabled_modules gate helper
    mitrabooks_connector.py
    legalmitra_connector.py   # stub → []
    mandirmitra_connector.py  # stub → []
    gruhamitra_connector.py   # stub → []
  ai/
    orchestrator.py         # summarize_email, generate_tasks, build_daily_brief
    prompts/
      summarize_email.txt
      generate_tasks.txt
      daily_brief.txt
    provider.py             # thin wrapper; fail closed / safe message
```

Frontend (MVP):

```text
frontend/mitrabooks-erp/
  … navigation entry for office_ai …
  modules/workspaces/office-ai/   # or equivalent workspace files
    tasks.js / email-summary.js / today-brief.js
```

### 4.2 Feature flags (granular)

Parent module `office_ai` must be in `enabled_modules`. Sub-features:

| Logical flag | Default when only `office_ai` enabled | Purpose |
| --- | --- | --- |
| `office_ai.tasks` | on | Task CRUD + generate |
| `office_ai.email` | on | Email paste + summarize |
| `office_ai.brief` | on | Daily brief |

Ops can disable one feature without killing the module:

- Prefer dotted keys in `enabled_modules` (e.g. keep `office_ai` + `office_ai.tasks` + `office_ai.brief`, omit `office_ai.email`), **or**
- Set tenant field `office_ai_features: ["tasks", "brief"]`.

If any `office_ai.*` key (or `office_ai_features`) is present, only listed sub-features are active. If only parent `office_ai` is present, all three are on.

### 4.3 Data model (Mongo only)

All documents include at minimum: `tenant_id`, `created_at`, `updated_at`, `created_by`, `updated_by` (user ids). Optional `change_reason` on user edits of AI-sourced rows.

#### `officemitra_tasks`

| Field | Type | Notes |
| --- | --- | --- |
| `title` | str | Required |
| `status` | enum | `open` \| `done` \| `cancelled` |
| `source` | enum | `manual` \| `ai` |
| `due_date` | datetime? | Optional |
| `linked_email_id` | ObjectId? | Optional |
| `notes` | str? | User-editable |
| `prompt_version` | str? | Set when `source=ai` |
| `ai_telemetry_id` | ObjectId? | Link to telemetry row |

#### `officemitra_emails`

| Field | Type | Notes |
| --- | --- | --- |
| `raw_text` | str | Paste-in MVP (no mailbox OAuth) |
| `summary` | str? | AI output |
| `suggested_task_ids` | list | Links to tasks created from this email |
| `prompt_version` | str? | Prompt used for summary |
| `ai_telemetry_id` | ObjectId? | Link to telemetry |

#### `officemitra_briefs`

| Field | Type | Notes |
| --- | --- | --- |
| `brief_date` | date | Calendar day for the brief |
| `generation_id` | str | UUID per generation (regenerate keeps history) |
| `generated_at` | datetime | When this generation ran |
| `content` | str | Generated narrative |
| `sections` | object | Structured facts from connectors **before** LLM prose |
| `connector_snapshot` | object | Raw connector payloads used (for audit/replay) |
| `source_modules` | list[str] | Which enabled modules contributed |
| `model` | str? | Provider model id |
| `prompt_version` | str | e.g. `daily_brief_v1` |
| `ai_telemetry_id` | ObjectId? | Link to telemetry |

Regenerate appends a new document (same `brief_date`, new `generation_id`); `GET .../briefs/today` returns the latest generation.

#### `officemitra_ai_telemetry`

| Field | Type | Notes |
| --- | --- | --- |
| `tenant_id` | str | Required |
| `feature` | str | `tasks` \| `email` \| `brief` |
| `provider` | str | e.g. `claude`, `null` |
| `model` | str | Model id |
| `prompt_version` | str | Versioned prompt id |
| `tokens_in` | int? | When provider returns usage |
| `tokens_out` | int? | When provider returns usage |
| `latency_ms` | int | Wall time |
| `estimated_cost` | str? | Decimal string; optional heuristic |
| `success` | bool | |
| `error_code` | str? | Safe code, no secrets |

**Indexes (planned):** `(tenant_id, status)`, `(tenant_id, brief_date, generated_at)`, `(tenant_id, created_at)`, `(tenant_id, feature, created_at)` on telemetry.

### 4.4 API surface (MVP)

All routes: `Authorization: Bearer`, `X-App-Key`, module `office_ai` enabled, matching sub-feature flag, tenant-scoped.

| Method | Path | Feature flag | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/officemitra/ping` | `office_ai` | Foundation smoke |
| GET/POST | `/api/v1/officemitra/tasks` | `office_ai.tasks` | List / create |
| PATCH | `/api/v1/officemitra/tasks/{id}` | `office_ai.tasks` | Update status/title (`updated_by`, optional `change_reason`) |
| POST | `/api/v1/officemitra/tasks/generate` | `office_ai.tasks` | AI: text → suggested tasks (persist optional) |
| GET/POST | `/api/v1/officemitra/emails` | `office_ai.email` | List / save paste |
| POST | `/api/v1/officemitra/emails/summarize` | `office_ai.email` | AI summary + optional task suggestions |
| GET | `/api/v1/officemitra/briefs/today` | `office_ai.brief` | Latest generation for today |
| POST | `/api/v1/officemitra/briefs/generate` | `office_ai.brief` | New generation via connectors + AI |

Error envelope: existing platform standard. AI provider down → soft-fail payload with `ai_available: false` (UI stays usable).

### 4.5 Connector contracts (read-only)

```python
# Conceptual — not production code yet

def require_module(tenant_ctx, module_key: str) -> bool: ...

# MitraBooks (real in Week 4)
def get_todays_revenue(tenant_id: str) -> dict: ...
def get_overdue_invoices(tenant_id: str, limit: int = 20) -> list[dict]: ...
def get_low_stock_alerts(tenant_id: str, limit: int = 20) -> list[dict]: ...  # optional MVP+

# Others (stub until Phase 3)
def get_pending_documents(tenant_id: str) -> list[dict]:
    return []

def get_open_maintenance_requests(tenant_id: str) -> list[dict]:
    return []

def get_upcoming_events_or_donations(tenant_id: str) -> list[dict]:
    return []
```

**Gating rule:** `build_daily_brief` calls a connector only if the corresponding product module is in `enabled_modules` (e.g. `business` / accounting for MitraBooks facts; `legal` for LegalMitra; `housing`; `temple`). If MitraBooks module is absent, brief still works from tasks/emails only.

### 4.6 AI layer (intentionally simple + replaceable)

```text
ai/
  provider.py              # Protocol + factory (ADR-006)
  providers/
    claude.py
    null_provider.py
  orchestrator.py
  prompts/
    summarize_email_v1.txt
    generate_tasks_v1.txt
    daily_brief_v1.txt
  telemetry.py
  metrics.py               # in-process counters: success/fail/latency/connector fail
```

```text
orchestrator.py
  ├── summarize_email(text) -> { summary, action_items?, prompt_version, telemetry }
  ├── generate_tasks(text) -> [{ title, due_date? }], prompt_version, telemetry
  └── build_daily_brief(...) -> { content, sections, generation_id, prompt_version, telemetry }
```

Rules:

- No agent framework, no OfficeMitra vector DB in MVP.
- Structured connector **facts** are assembled in code; LLM turns them into readable prose — do not ask the model to invent revenue numbers.
- Flag AI-sourced tasks with `source=ai`.
- Persist `prompt_version` + telemetry on every AI write.
- Never log full confidential email bodies to shared debug logs in production configs.
- Outputs are advisory; UI disclaimer: not final legal/financial advice.
- Eval fixtures live under `tests/ai/officemitra/` (summaries, tasks, briefs) for prompt regression.

### 4.7 Guardrails (must appear in AGENTS.md)

OfficeMitra **must never** (MVP and until a write-automation ADR):

- Post journal entries or mutate ledger balances
- Create/approve invoices, bills, credit/debit notes
- File GST / TDS returns
- Send legal notices or mutate LegalMitra matter custody
- Query another product’s Mongo/Postgres directly
- Trust `tenant_id` from the client body
- Call InvestMitra or include investment modules in unified registry

OfficeMitra **must**:

- Scope every query by `tenant_id`
- Gate routes by `office_ai` + `app_key` + RBAC
- Gate connectors by `enabled_modules`
- Mark AI-generated tasks as AI-sourced
- Fail safely when the AI provider is missing or errors

---

## 5. Module registry design (to add)

```json
{
  "module_key": "office_ai",
  "display_name": "OfficeMitra AI",
  "allowed_organization_types": ["BUSINESS", "PROFESSIONAL", "HOUSING", "TEMPLE", "LEGAL"],
  "allowed_app_keys": ["officemitra", "mitrabooks", "legalmitra", "gruhamitra", "mandirmitra"],
  "minimum_plan": "pro",
  "default_enabled": false,
  "routes": ["/api/v1/officemitra"],
  "features": ["tasks", "email", "brief"]
}
```

Notes:

- `default_enabled: false` — opt-in per tenant until pricing/ops decide otherwise.
- Explicit app-key list (not `*`) keeps auth boundaries clear; standalone clients use `officemitra`.
- Update `docs/architecture/MODULE_REGISTRY.md` and `docs/standards/NAMING_CONVENTIONS.md` when implementing.
- When MitraBooks (or other) modules are present, OfficeMitra consumes them through the Connector Manager / service interfaces. When absent, those capabilities are unavailable and OfficeMitra continues with native functionality.

---

## 6. Week-by-week delivery (MVP = Weeks 0–5)

### Week 0 — Decisions & docs (no product UI)

| # | Work item | Deliverable | Done when |
| --- | --- | --- | --- |
| W0.1 | ADRs | ADR-001…005 + `docs/adr/README.md` | Present in repo (this change set) |
| W0.2 | This plan approved | Product owner sign-off on §0 locked decisions | Checkbox below |
| W0.3 | Traceability | Link plan from PRD or architecture index if required by owner | Optional |

**Acceptance:** Locked decisions undisputed; InvestMitra excluded; OS positioning rejected.

### Week 1 — Foundation (confirm & extend, not rebuild)

| # | Work item | Deliverable |
| --- | --- | --- |
| W1.1 | AGENTS.md | New § OfficeMitra AI guardrails (connectors, read-only, AI flags, no InvestMitra) |
| W1.2 | Registry | Add `office_ai` design + access helper wiring for one route |
| W1.3 | Scaffold | Package layout under `app/modules/office_ai/` (empty services OK) |
| W1.4 | Ping | `GET /api/v1/officemitra/ping` protected + tenant/module checks |
| W1.5 | Shell stub | Nav item “Office AI” visible only when `office_ai` enabled (can be placeholder page) |
| W1.6 | Tests | Deny without module; deny wrong tenant; ping allow when enabled |

**Acceptance:** Ping works on a demo tenant with `office_ai` enabled; denied otherwise.

### Week 2 — Task Generator

| # | Work item | Deliverable |
| --- | --- | --- |
| W2.1 | Mongo model + indexes | `officemitra_tasks` |
| W2.2 | CRUD APIs | List/create/patch |
| W2.3 | AI `generate_tasks` | Provider wrapper + prompt; `source=ai` |
| W2.4 | UI | Paste/text → suggested tasks → save/edit/complete |
| W2.5 | Tests | Tenant isolation; AI flag persisted; provider-missing fallback |

**Acceptance:** User can create manual and AI-suggested tasks without any MitraBooks connector.

### Week 3 — Email Summary

| # | Work item | Deliverable |
| --- | --- | --- |
| W3.1 | Mongo model | `officemitra_emails` |
| W3.2 | Paste-in only | No Gmail OAuth |
| W3.3 | `summarize_email` | Summary + optional task suggestions wired to task service |
| W3.4 | UI | Email paste → summary → accept/reject suggested tasks |
| W3.5 | Tests | Tenant isolation; link email↔tasks; no cross-tenant leak |

**Acceptance:** Full email→summary→tasks loop without external mailbox APIs.

### Week 4 — Daily Brief + MitraBooks connector

| # | Work item | Deliverable |
| --- | --- | --- |
| W4.1 | `mitrabooks_connector` | At least `get_todays_revenue`, `get_overdue_invoices` via **business/accounting services** |
| W4.2 | Stub connectors | Legal / Mandir / Gruha return `[]` |
| W4.3 | Module gating | Skip connector if module not enabled |
| W4.4 | `build_daily_brief` | Facts from connectors + today’s tasks/emails → one LLM call; store brief |
| W4.5 | UI | “Today” page |
| W4.6 | Tests | Connector not called when module disabled; no direct DB access in office_ai toward accounting tables; brief stores `source_modules` |

**Acceptance:** Brief reflects real MitraBooks numbers for an enabled business tenant; stubs never crash.

### Week 5 — Integration harden + polish

| # | Work item | Deliverable |
| --- | --- | --- |
| W5.1 | E2E smoke | Login → tasks → email summary → brief with MitraBooks facts (demo tenant) |
| W5.2 | Preflight | `python scripts/preflight.py` (+ `--frontend` if shell changed) |
| W5.3 | Docs sync | MODULE_REGISTRY, CURRENT_VS_TARGET note for OfficeMitra “planned→MVP” |
| W5.4 | Retention | Align email/brief retention with tenant policy stubs (no forever PII by accident) |
| W5.5 | Fix only | No new features |

**MVP exit criteria:** Three features live on staging demo tenant; ADRs respected; InvestMitra untouched; no write paths into other products.

### Weeks 6–8 (stretch / Phase 3 — only after MVP live)

| Week | Connector | Source facts (examples) |
| --- | --- | --- |
| 6 | LegalMitra | Documents/matters pending review (service-layer only) |
| 7 | GruhaMitra | Open maintenance requests |
| 8 | MandirMitra | Upcoming events / donations due |

Each week is isolated **because** the connector pattern already exists.

---

## 7. Frontend placement (nuanced)

| Horizon | Choice | Rationale |
| --- | --- | --- |
| **MVP (now)** | Panel inside **MitraBooks ERP shell** | Audience already on ERP; one deployable shell; permissions-driven nav |
| **Later (optional)** | Standalone OfficeMitra productivity app | Serves users who want AI tasks/email/brief **without** full ERP — still not the platform OS; still uses connectors when ERP modules are enabled |

Do not build both UIs in MVP.

---

## 8. Testing plan (risk-matched)

| Risk | Tests |
| --- | --- |
| Tenancy | CRUD and list never return other tenants’ tasks/emails/briefs |
| Module access | Routes 403/deny when `office_ai` disabled |
| App key | Reject disallowed `X-App-Key` |
| Connector isolation | Unit/static check or test double proving office_ai does not open accounting Session/Mongo collections directly |
| Enabled modules | Brief skips Legal connector when `legal` not enabled |
| AI fallback | Missing API key → safe response, no 500 stack leak |
| AI provenance | Generated tasks have `source=ai` |
| Accounting safety | No OfficeMitra path can post journals (route/contract test) |

Commands (when code exists):

```powershell
python -m compileall app scripts tests
python -m pytest tests/test_office_ai*.py -v
python scripts/preflight.py
python scripts/preflight.py --frontend
```

---

## 9. Security & privacy checklist

- [ ] No secrets in prompts committed to git
- [ ] No logging of bearer tokens, provider API keys, or full payment payloads
- [ ] Tenant policy before sending email body to external AI provider (reuse platform AI settings pattern where it exists)
- [ ] Advisory disclaimer on Brief and Email Summary UI
- [ ] Human review before any future write automation (Phase 4)
- [ ] Demo-tenant only for destructive E2E

---

## 10. Documentation & policy updates (implementation checklist)

| Doc | Change |
| --- | --- |
| `AGENTS.md` | Add OfficeMitra AI section; PR checklist remains intact |
| `docs/architecture/MODULE_REGISTRY.md` | Add `office_ai` row |
| `docs/standards/NAMING_CONVENTIONS.md` | Add `office_ai` / optional future `officemitra` app key note |
| `docs/architecture/CURRENT_VS_TARGET.md` | Row for OfficeMitra current=absent / target=thin AI layer |
| `docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md` | Short “planned additive module” mention only after owner approval — do not imply shipped |
| `docs/adr/*` | Already created for D1–D5 |

Master PRDs remain non-negotiable; OfficeMitra must not contradict MitraBooks-as-core or InvestMitra exclusion.

---

## 11. PR sequencing (suggested)

| PR | Scope | Notes |
| --- | --- | --- |
| PR-A | Docs: ADRs + this plan + AGENTS.md section (no feature UI) | Low risk |
| PR-B | Backend scaffold + ping + registry + tests | Foundation |
| PR-C | Tasks + AI generate | Feature 1 |
| PR-D | Emails + summarize | Feature 2 |
| PR-E | MitraBooks connector + brief + shell Today page | Feature 3 |
| PR-F | Polish, retention, staging smoke notes | MVP close |

Do not combine PR-E with unrelated MitraBooks ERP gap work.

---

## 12. Rollback

| Layer | Rollback |
| --- | --- |
| Feature flag | Disable `office_ai` on tenant (`enabled_modules`) — UI and API deny |
| Code | Revert OfficeMitra PRs; no accounting schema migrations in MVP |
| Data | Mongo collections can remain dormant; purge only with explicit tenant/ops approval |
| AI provider | Turn off provider env → endpoints soft-fail; core ERP unaffected |

No ledger reversal needed for MVP (no accounting writes).

---

## 13. Open items (resolve before Week 4)

| # | Question | Proposed default |
| --- | --- | --- |
| O1 | Exact MitraBooks service functions for revenue/overdue | Prefer existing report/statement service methods; document chosen call sites in connector | 
| O2 | One brief per tenant-day upsert vs append history | Upsert `brief_date` + keep prior versions in `history[]` if needed |
| O3 | Which org types get `office_ai` by default | Default **off** for all; enable on demo BUSINESS first |
| O4 | Provider (Claude vs existing platform AI settings) | Reuse existing tenant/platform AI config pattern if present; else env-gated provider like Legal AI |
| O5 | Soft-fail vs HTTP error for AI outages | Soft-fail with `ai_available: false` for generate endpoints so UI stays usable |

---

## 14. Approval gate

| Check | Owner |
| --- | --- |
| §0 locked decisions accepted | Product owner |
| ADRs accepted | Product owner / architect |
| MVP = three features only | Product owner |
| UI = MitraBooks shell for MVP | Product owner |
| InvestMitra excluded | Confirmed by AGENTS.md |
| Start Week 1 code only after PR-A docs merge (or explicit waive) | Maintainer |

**Approval:**

- [ ] Approved to implement Week 1+ as written  
- [ ] Approved with amendments: _______________________  
- [ ] Not approved — revise plan  

---

## 15. PR acceptance mapping (AGENTS.md §25)

When OfficeMitra PRs merge, each PR description must confirm:

- Tenant isolation on all OfficeMitra reads/writes  
- App-key + `office_ai` module access  
- No accounting invariant risk (read-only connectors)  
- Cross-DB: N/A for MVP writes; briefs do not mark ERP transactions complete  
- Current vs target language in docs  
- Frontend: shell module only; LegalMitra separate; InvestMitra excluded  
- No secrets committed  
- Rollback via module disable  
- Tests for changed risk  
- `python scripts/preflight.py` (+ `--frontend` when UI changes)  
- No blocked destructive shell commands  

---

## Document history

| Version | Date | Notes |
| --- | --- | --- |
| 1.0 | 2026-08-05 | Initial detailed plan from architecture review + post-review alignment note |
| 1.1 | 2026-08-05 | Approved; added success criteria, feature flags, telemetry, prompt versioning, brief generations, ADR-006, eval/observability |
| 1.2 | 2026-08-05 | Modular deployment (ADR-007): Connector Manager, deployment profiles, `officemitra` app key, standalone-safe Daily Brief |
| 1.3 | 2026-08-05 | Phase 1 complete locally: retention helper, Mongo isolation tests, smoke checklist |
