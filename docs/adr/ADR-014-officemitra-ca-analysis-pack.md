# ADR-014: OfficeMitra CA Analysis Pack (MIS assembly, narrative, export)

**Status:** Accepted  
**Date:** 2026-08-11  
**Accepted:** 2026-08-11  
**Product scope:** OfficeMitra AI — CA / CFO MIS workflows (post foundation smoke)  
**Depends on:** [ADR-002](ADR-002-officemitra-connectors-only.md) (connectors only), [ADR-006](ADR-006-ai-providers-replaceable.md) (AI providers), [ADR-008](ADR-008-officemitra-confirmed-writeback.md) (proposals + Action Registry), [ADR-012](ADR-012-officemitra-policy-engine.md) (policy before export/execute)  
**Optionally uses:** [ADR-009](ADR-009-officemitra-workflow-engine.md) (scheduled MIS pack runs), [ADR-010](ADR-010-officemitra-companion-writeback.md) (live MitraBooks reads — still Proposed for writes)  
**Related:** [ADR-007](ADR-007-officemitra-modular-deployment.md) (standalone CA tenants), [ADR-013](ADR-013-officemitra-workflow-template-library.md) (curated MIS workflow templates — Future)  
**Does not supersede:** [ADR-001](ADR-001-mitrabooks-transactional-core.md) (MitraBooks remains books of record for ERP tenants), [ADR-003](ADR-003-no-cross-product-db-access.md), accounting doctrine in `AGENTS.md` §10  

## Context

OfficeMitra foundation (Phases 1–6 + ADR-012 Policy Engine) delivers tasks, paste-in productivity, daily brief, confirmed OfficeMitra-owned writes, workflows, and centralized policy. That layer is **not** a monthly MIS factory.

CA firms and business CFOs routinely need a **period-close MIS pack**: P&L and balance-sheet views, budget-vs-actual variance, cash and ageing summaries, vertical KPIs, executive narrative, and board-ready exports (Excel drill-down, one-page PDF, slide deck). Sources vary:

- **Excel / CSV** from clients on Tally, legacy ERP, or manual books (common for CA practices).
- **Live reads** from MitraBooks accounting services (SanMitra ERP tenants).
- **External cloud books** (Zoho Books, QuickBooks, etc.) — later, via connector adapters.

Industry structure is **core-plus-variable**: ~60–70% of metrics (P&L, BS, cash, BvA, ageing) are universal; ~30–40% differ by business type (manufacturing, services, housing society, temple trust, SaaS). A single hardcoded MIS tree will not scale across SanMitra org types or standalone CA buyers.

OfficeMitra must remain a **thin orchestration layer**: it assembles drafts, generates attributed narrative, and exports artifacts. It does **not** become the system of record for client books, post journals, or present AI output as final statutory or board numbers without human reconciliation and sign-off.

**Accepted 2026-08-11** after product-owner review (foundation smoke may complete in parallel; implementation must not bypass ADR-012 or accounting boundaries).

## Current state vs target state

| Area | Current (today) | Target (this ADR) |
| --- | --- | --- |
| Daily brief | Lightweight connector facts for “today” (`get_todays_revenue`, overdue AR) | Unchanged; brief stays separate from MIS |
| MIS assembly | Not implemented | Period-close **MIS pack** from normalized facts + metric pack rules |
| Ingestion | Internal SanMitra connectors only (brief-oriented) | **Excel/import first**, then extended MitraBooks MIS reads; external ERP read adapters deferred |
| Canonical facts | Ad-hoc brief sections | Versioned **MIS fact store** with source attribution |
| Narrative | Brief prompts | Variance commentary with **fact citations**; no invented figures |
| Export | None | Proposed → confirmed → **export** (Excel, PDF summary, PPT template) behind policy |
| Books of record | MitraBooks PostgreSQL for ERP tenants | Unchanged; OfficeMitra owns **draft packs** in Mongo only |

### Gap (must be built)

- Module sub-features and registry entries for `office_ai.mis` (+ pack keys).
- MIS fact schema, import connector, pack registry, `mis_service` (assemble / reconcile / narrative).
- Policy-gated export actions in Action Registry.
- UI workspace: upload → preview facts → draft pack → reconcile/sign-off → export (with fact citation UI).
- Tests: tenant isolation, no invented numbers when facts missing, policy deny on export without reconcile, import validation errors surfaced, immutability after reconcile/export.

### Deferred (explicit non-goals for first CA Analysis Pack slice)

- Tally local companion agent or live Tally sync.
- Zoho / QuickBooks OAuth connectors (plan as follow-on ADR for **external ERP** adapters).
- ADR-010 companion writes (journals, invoices, GST filing).
- Auto-send to board / WhatsApp / email without explicit export confirm.
- Arbitrary client Excel fuzzy mapping (non-template workbooks) — deferred until v1 template path is stable.
- OfficeMitra-owned vector RAG over client uploads (retention policy may come later).
- InvestMitra or any unified-scope expansion.

## Decision

### 1. Product: CA Analysis Pack

Introduce **OfficeMitra CA Analysis Pack** as a gated capability under module `office_ai`:

```text
Sources (Excel | MitraBooks connector | future external adapter)
        ↓
Import / sync → normalize → MIS fact store (Mongo, tenant-scoped)
        ↓
Metric pack (vertical KPI + materiality rules + pack_version)
        ↓
MIS assembly (tables, variances, charts metadata, data_quality_score)
        ↓
AI narrative (attributed, fail-soft per audience) — ADR-006
        ↓
Human reconcile + sign-off (required before “final” export)
        ↓
Policy evaluation (ADR-012) → export actions (ADR-008 registry)
        ↓
Artifacts: Excel workbook, CEO one-pager PDF, board slide deck (template-driven)
```

**Daily brief and MIS pack are separate services.** They may share connector infrastructure but must not share prompts, cadence, or “final number” semantics.

**Connector relationship (ADR-002):** MIS ingestion uses the **same adapter discipline** as daily-brief connectors — thin modules calling service layers or import parsers, returning plain JSON. `MISFact` is a **specialized extension** of the canonical connector shape (`source_system`, `source_id`, tenant-scoped dicts). MIS adapters may share internal plumbing with brief connectors but write to the **MIS fact store**, not brief sections. There is not a second competing connector design.

### 2. MIS fact layer (canonical, source-agnostic)

All ingestion adapters map into flat JSON-shaped **MIS facts** (ADR-002 discipline). Every fact record includes at minimum:

| Field | Purpose |
| --- | --- |
| `tenant_id` | Tenancy |
| `fact_id` | Stable id for narrative citation |
| `entity_type` | e.g. `pnl_line`, `bs_line`, `cash_summary`, `aging_bucket`, `kpi`, `party` |
| `period` | e.g. `2026-07` (month) or FY range |
| `as_of` | Snapshot date |
| `source_system` | `excel_import` / `mitrabooks` / `zoho` / `tally` (future) |
| `source_id` | Original row/voucher/id in source |
| `source_ref` | File name, sheet, row, or API endpoint |
| `amount` / `value` | Fixed-precision decimal or integer minor units — **never float** |
| `currency` | ISO code |
| `dimensions` | Optional: department, cost center, product line, region |
| `reconciled` | `false` until human marks reconciled for the pack |
| `pack_id` | Owning MIS pack draft |
| `immutable` | `false` in draft; `true` after pack reconcile (see §5) |

**Core entity shapes (initial set):**

| Entity | Core fields |
| --- | --- |
| `MISPnLLine` | account/group, actual, budget, prior_period, variance_abs, variance_pct |
| `MISBalanceSheetLine` | account/group, balance, prior_balance |
| `MISCashSummary` | opening, operating, investing, financing, closing, runway_months (optional) |
| `MISAgingBucket` | kind (`receivable`/`payable`), party_ref, bucket, amount |
| `MISKPI` | kpi_key, label, value, unit, target (optional) |
| `MISParty` | name, type, gstin (optional), concentration_rank (optional) |

**Ledger entries from external sources are read-only in OfficeMitra.** No adapter may expose a write path that inserts journal rows. Financial effect in MitraBooks tenants still flows only through MitraBooks accounting services ([ADR-001](ADR-001-mitrabooks-transactional-core.md)).

Store normalized facts in tenant-scoped Mongo (e.g. `officemitra_mis_facts` / `officemitra_mis_packs`).

### 3. Metric packs (config-driven, not hardcoded)

Vertical behavior is selected by **metric pack** configuration:

| Pack key | Primary use | Extra KPIs (examples) |
| --- | --- | --- |
| `sme_general` | SME CFO monthly pack | BvA by department, top customers, DSO/DPO |
| `professional_services` | CA / consulting clients | utilization, WIP, billing realization |
| `manufacturing` | Plant CFO | inventory turnover, RM variance, capacity |
| `housing` | GruhaMitra-aligned societies | collection efficiency, maintenance fund adequacy |
| `temple` | MandirMitra-aligned trusts | donation mix, corpus vs revenue |
| `ca_practice` | CA firm roll-up (multi-client) | client status, compliance flags, period checklist |

Each pack defines:

- `pack_key` + **`pack_version`** (semver, e.g. `sme_general@1.0.0`) — stored on every assembled pack and export artifact for reproducibility.
- Required and optional `entity_type` sets.
- KPI formulas referencing MIS facts (deterministic code, not LLM math).
- Default charts (type + fact bindings).
- **Materiality thresholds** (variance % / absolute) for exception flags.
- **`materiality_rule_version`** — semver for the threshold set used when the pack was assembled (historical reports remain interpretable if thresholds change later).
- Narrative prompt template version (`prompt_version` per ADR-006 telemetry).

Packs are data/config first; code registers pack loaders. Adding a pack must not require changing policy or export plumbing. KPI formula changes ship as new `pack_version` values; prior versions remain loadable for audit comparison.

### 4. Data quality score (single trust signal)

Each MIS pack carries one derived **`data_quality_score`** (0–100) and a structured **`data_quality_breakdown`**, computed deterministically — **not** from the AI model:

| Input | Effect on score |
| --- | --- |
| Required entity types present | Weighted positive |
| Row-level validation errors | Deduction per error |
| Unmapped / skipped import rows | Deduction |
| Missing budget or prior-period columns | Deduction |
| Reconciliation completeness (% facts marked reviewed) | Factor at reconcile time |

Display bands (UI):

| Score | Label | Meaning |
| --- | --- | --- |
| 90–100 | High | Suitable for executive export after reconcile |
| 70–89 | Medium | Review gaps before board-facing export |
| &lt; 70 | Low | Block PPT export by policy default; Excel still allowed for investigation |

Do **not** add a separate AI `confidence_level` — one score avoids conflicting trust signals. Narrative sections may reference the pack score in disclaimers when &lt; 90.

### 5. MIS pack lifecycle and fact immutability

| State | Meaning | Fact mutability |
| --- | --- | --- |
| `draft` | Facts imported; assembly in progress | **Editable** — re-import, correct mappings, delete facts |
| `pending_reconcile` | Tables/charts generated; awaiting human review | **Editable** — corrections allowed until reconcile |
| `reconciled` | Named actor marked numbers reviewed for this period | **Locked** — facts immutable; new corrections require new pack revision |
| `pending_export` | Narrative approved; export proposal open | **Locked** |
| `exported` | Artifacts generated and stored (audit) | **Immutable** — pack + facts + narrative + artifact refs frozen |
| `failed` | Assembly or export error | Editable only by reverting to `draft` (audit event required) |

**Rule:** Facts are **immutable after reconciliation.** Exported packs are fully immutable. Corrections after reconcile ship as a **new pack revision** (`pack_id` + `revision` or successor link), never silent in-place edits. This is mandatory for CA/CFO auditability (“can a past board pack silently change?” → **no**).

AI may assist in `draft` → `pending_reconcile`. Transition to `reconciled` requires an authenticated human action (CA / CFO role). Export requires **policy evaluation** (ADR-012).

### 6. Excel import strategy (v1 locked)

**v1 (first slice): mandatory SanMitra CA import template** — fixed sheet names and column contract documented in operations runbook. CAs map client data into the template (or deliver pre-formatted exports). Import validates row-by-row; errors surface with sheet/row/column refs.

**Deferred (not v1):** arbitrary client workbook fuzzy mapping and saved per-client column mapping profiles. Those ship only after template import passes staging smoke.

Rationale: template-first minimizes mapping entropy (merged headers, inconsistent sheet names) and keeps the first slice shippable; flexible mapper is a separate product increment.

### 7. Ingestion paths (sequenced)

| Priority | Path | Notes |
| --- | --- | --- |
| **1** | **Excel / CSV import (template)** | SanMitra template → MIS facts; validation errors per row |
| **2** | **MitraBooks MIS connector** | Extend read connector to call accounting **report services** (P&L, BS, ageing, cash) — never raw SQL |
| **3** | **External cloud adapter** (e.g. Zoho) | Read-only; maps API/MCP objects → MIS facts; stale-data TTL on cache |
| **4** | **Tally companion agent** | Separate track; read-only until reliable ack; not in first slice |

Import connector implements the same **read/normalize** contract as internal connectors:

```text
ingest(tenant_id, source, payload) -> list[MISFact] + validation_report + data_quality_breakdown
```

Stub importers returning empty facts with explicit `validation_report.errors` are valid during scaffold.

### 8. Narrative and AI rules

- Narrative generation uses ADR-006 providers only through the orchestrator; **fail soft** — never invent revenue, variance, or ratios.
- Every narrative bullet must reference one or more `fact_id` values; **UI must show citations** (hover/link to source row).
- Prompts are versioned files; store `prompt_version`, provider telemetry, and `source=ai` on generated sections.
- Disclaimers: **draft for review — not final financial advice or statutory filing.**

**Fail-soft by audience** (missing facts or low `data_quality_score`):

| Artifact | Behavior when data gap |
| --- | --- |
| **CFO Excel** | Inline cell/note: `DATA UNAVAILABLE — see import log`; full validation sheet included |
| **CEO PDF summary** | Omit section or show “Insufficient data for this metric”; never blank placeholder boxes |
| **Board PPT** | Slide footnote + skip chart; policy may block export entirely when score &lt; 70 |

### 9. Export actions (OfficeMitra-owned artifacts)

Register export actions in the Action Registry (ADR-008), `target_module=office_ai`, gated by `office_ai.mis` and `office_ai.mis.export`:

| Action | Risk | Policy default |
| --- | --- | --- |
| `export_mis_excel` | **MEDIUM** | Reconcile + confirmation |
| `export_mis_pdf_summary` | **MEDIUM** | Reconcile + confirmation |
| `export_mis_ppt` | **HIGH** | Reconcile + confirmation; **maker-checker default on** for board-facing deck |

Board PPT has higher blast radius than internal CFO workbook — risk tier drives ADR-012 maker-checker without treating all exports uniformly.

Exports write to OfficeMitra-owned storage references (Mongo metadata + object store path TBD). They do **not** write back to client ERP/Tally/Zoho in v1.

Workflows (ADR-009) may chain: `import_complete → assemble → notify_reviewer → (after reconcile) export` when `office_ai.workflows` is enabled — still subject to policy per step.

### 10. Feature flags (default off)

| Flag | Default | Purpose |
| --- | --- | --- |
| `office_ai.mis` | off | Parent MIS capability |
| `office_ai.mis.import` | off | Excel/CSV template upload |
| `office_ai.mis.live_mitrabooks` | off | Live ERP reads (requires business/accounting modules) |
| `office_ai.mis.export` | off | PDF/Excel/PPT export actions |
| `office_ai.mis.pack.<key>` | off | Per-pack enablement |

Parent `office_ai` alone does **not** enable MIS. Standalone CA tenants may enable `office_ai` + `office_ai.mis` + import/export without MitraBooks modules.

### 11. Audience outputs (layered deliverables)

| Audience | Artifact | Content |
| --- | --- | --- |
| CEO | 1-page PDF summary | Trends, exceptions, decisions needed |
| CFO | Excel workbook | Pivot-friendly tables, variance columns, source tags |
| Board | PPT (8–10 slides) | Story-driven deck from reconciled pack + approved narrative |

One MIS pack draft feeds all three; export actions may be selective.

### 12. Deployment personas (ingestion paths)

OfficeMitra supports **two front doors** to the same MIS engine. The persona differs by who runs OfficeMitra and how data arrives; the **CEO/CFO/board artifacts** are the same pipeline after reconcile.

| Persona | Typical org | Ingestion path | Who generates MIS | Who receives export |
| --- | --- | --- | --- | --- |
| **In-house accountant** | `BUSINESS` tenant on MitraBooks (or future Zoho connector) | **Path A — Connector read** (`office_ai.mis.live_mitrabooks` or external adapter) | Company accountant with `office_ai.mis` | CEO/CFO/internal board — PDF/Excel/PPT after accountant reconcile |
| **CA firm staff** | `PROFESSIONAL` tenant (`officemitra` standalone or ERP shell) | **Path B — Excel upload** (client sends workbook) and/or **Path A** when client grants connector access per client entity | CA preparer with `office_ai.mis` + `ca_practice` pack | Client CEO/CFO — exports sent manually by CA (auto-send deferred) |
| **Client upload-only** | Client does **not** use OfficeMitra | **Path B only** — client emails/exports Excel → CA uploads SanMitra template | CA firm only | Client leadership receives CA-delivered pack |
| **Hybrid** | CA manages many clients | Per client: Path B until connector creds exist; Path A when live read enabled on that client's tenant/entity | CA or delegated client accountant if tenant access shared | Same as above |

**Path A (connector):** OfficeMitra pulls read-only facts from the books system (MitraBooks report services, later Zoho/Tally). The **accountant or CA** with tenant access runs assemble → narrative → **reconcile → export**. The CEO/CFO does not need OfficeMitra login — they receive the artifact after human sign-off.

**Path B (Excel):** Client downloads from Tally/legacy ERP or sends existing sheets; CA or in-house accountant maps to the **SanMitra CA import template** and uploads. Same MIS pack lifecycle as Path A.

**Governance is identical for both paths:** no invented figures, `data_quality_score` on the pack, facts **immutable after reconcile**, PPT export defaults to maker-checker (HIGH risk). Connectors do **not** post journals or replace the books of record.

**Multi-client CA note:** each client should remain a **separate tenant** (or explicitly scoped entity) — no cross-tenant fact sharing without admin action. `ca_practice` pack supports roll-up views only from tenant-scoped packs the CA is authorized to read.

### 13. Hard exclusions (remain forbidden unless a later ADR)

- Posting or editing journals, invoices, or payments in MitraBooks or external ERP from MIS flows.
- GST/TDS **filing** or government portal submission.
- Presenting unreconciled AI narrative as “signed MIS” or board-final.
- In-place edits to reconciled or exported packs/facts.
- Cross-tenant fact leakage or pack sharing without explicit tenant admin action.
- InvestMitra connectors or entitlements.

External ERP **read** adapters and **allowlisted note/draft writes** remain governed separately (future **external ERP connector ADR**; do not fold into ADR-010 without product-owner review).

## Architecture sketch

```text
┌─────────────────────────────────────────────────────────────┐
│ OfficeMitra CA Analysis Pack                                 │
│  mis_service │ pack_registry │ narrative │ export_handlers    │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
        Policy Engine (ADR-012)         Action Registry (ADR-008)
                │                               │
        ┌───────┴────────┐              Workflow (ADR-009, opt)
        │ Connector tier │  ← same ADR-002 adapter pattern as brief
        └───────┬────────┘
                │
    ┌───────────┼───────────┬──────────────┐
    │           │           │              │
 excel_import  mitrabooks   (zoho)      (tally agent)
  connector    mis_read    future        future
        ↓
   MIS fact store (not brief sections)
```

## Implementation sequencing

1. **Registry + flags** — `office_ai.mis*` entries in module registry; routes stubbed behind module gate. — **Done**
2. **MIS fact schema + Mongo collections** — indexes on `tenant_id`, `pack_id`, `period`; immutability enforcement. — **Done**
3. **Excel template import + validation UI** — SanMitra template only; no AI until facts persist.
4. **Pack `sme_general@1.0.0` + `ca_practice@1.0.0`** — deterministic KPI/variance assembly; `materiality_rule_version`.
5. **Narrative with citations + fact citation UI** — orchestrator + tests for “no facts → no numbers.” — **Done** (UI: Generate narrative + clickable `fact_id` chips on MIS Packs)
6. **`data_quality_score` computation** — deterministic breakdown; PPT block when &lt; 70.
7. **Reconcile + export actions** — differentiated risk tiers; maker-checker default for PPT.
8. **MitraBooks MIS read connector** — report services only (ADR-002).
9. **PPT/PDF templates** — branded, template-driven; audience-specific gap rendering; no LLM layout for v1.

Do **not** start external ERP, arbitrary Excel mapping, or Tally agent work until steps 1–7 pass staging smoke on a demo CA tenant.

## Consequences

- OfficeMitra gains a second major capability beside daily brief: **period-close MIS**, aligned with CA market opportunity.
- Connector Manager grows a **MIS ingestion** registry distinct from brief `collect` functions (same ADR-002 adapter pattern).
- MitraBooks ERP remains transactional core; MIS reads defer to accounting services.
- Foundation staging smoke (Phases 4–6 + ADR-012) should complete before production MIS enablement; local implementation may proceed against demo tenants.
- Tests must cover: import validation, pack isolation, reconcile gate, immutability after reconcile/export, narrative without facts, policy deny paths, PPT maker-checker default, fixed-precision amounts, `data_quality_score` bands.
- Pack/version metadata on every export supports reproducibility and CA audit questions.

## Acceptance criteria (recorded at Accept — 2026-08-11)

Product owner confirmed:

1. First metric packs: **`sme_general@1.0.0`**, **`ca_practice@1.0.0`**; Excel **template-first** import (flexible mapper deferred).
2. Reconcile required before export; **PPT export defaults to maker-checker** (HIGH risk); Excel/PDF MEDIUM with confirmation.
3. Foundation staging smoke may complete in parallel; production MIS gated on signoff.
4. Implementation plan updated with Phase 7 CA Analysis Pack path.
5. **Fact citation UI** required in narrative review screen.
6. **`data_quality_score`** (single trust signal) required on pack summary; PPT blocked when &lt; 70 by default.
7. **`pack_version`** + **`materiality_rule_version`** stored on every pack and export artifact.
8. **Fact immutability after reconcile/export** — corrections via new pack revision only.

Implementation is **authorized** under this ADR subject to the flags, exclusions, and sequencing above.
