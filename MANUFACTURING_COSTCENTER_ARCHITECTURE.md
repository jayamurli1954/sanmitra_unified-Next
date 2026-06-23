# Manufacturing & Cost-Centre Accounting — Enterprise Add-On

**Status:** Phase 1 in progress · **Posture:** opt-in, per accounting entity · **AI:** none in v1 (deterministic only)

## Origin & sourcing policy

This feature was prompted by a Gemini-generated review doc (`manufacturing_cost-center_module.docx`).
That document is **reference only**. None of its code, schemas, or API shapes are used:
its parallel `GLEntry`/`CostCenter` tables, OpenAI calls, `BackgroundTasks` financial posting,
`float` money math, and nonstandard HTTP codes are all rejected as wrong for this stack.

**Ideas** are borrowed from **ERPNext + Frappe**, cloned into `external-repos/` (already gitignored,
reference-only, never imported, never deployed — same pattern used for `frappe-hrms` in the HR add-on).
Borrowed as ideas, not cloned as a replica.

**Implementation** uses this repo's own proven patterns:
- the existing `app/accounting/` double-entry SQL ledger (extending `JournalLine` exactly as `party_id` already works),
- `app/modules/business/dimensions.py` cost-centre masters,
- `app/modules/business/inventory.py` item master + weighted-average stock register,
- the HR add-on's two-flag gating model,
- `Decimal` money math, synchronous + idempotent posting, report-tab UI convention.

## Opt-in model (strictly per accounting entity)

Two **independent** flags, both default **off**, both requiring platform provisioning first.
A business that doesn't want either sees nothing: no menu, no tabs, no COA accounts, no behaviour change.

| Layer | Cost centres | Manufacturing |
|---|---|---|
| Platform-owner provisioning (tenant record) | `cost_centre_addon_available` | `mfg_addon_available` |
| Tenant-admin enable (InvoiceSettings) | `cost_centre_enabled` | `manufacturing_enabled` |

- Scoped per `tenant_id` + `accounting_entity_id` — enable for the one manufacturing entity, leave trading/service entities untouched.
- **Manufacturing depends on cost centres** — enabling manufacturing auto-requires cost centres enabled.
- Frontend uses a never-403 probe (`resolve_*_access`) so the workspace renders only where enabled; every other tenant's UI is unchanged.

## Phase 1 — Cost-Centre Accounting (backbone, ships first)

Independently valuable to non-manufacturers (departments/branches/projects).

- **1a. Ledger-line dimension** — nullable `cost_center_id` on `JournalLine`, mirroring `party_id`. Alembic `0011`, additive + indexed, backward-compatible.
- **1b. Thread through posting** — `JournalLineIn` + `post_journal_entry` + reversal carry `cost_center_id`. Optional everywhere; existing callers unchanged.
- **1c. Hierarchy** — add `parent_code` roll-up to the existing `business_dimensions` cost-centre masters.
- **1d. Budgets** — `business_cost_centre_budgets` collection, per cost-centre/period/account (DRAFT→APPROVED→LOCKED).
- **1e. Reports** — Cost-Centre P&L, Budget-vs-Actual, roll-up tree as tabs in Financial Statements, CSV/Excel via `report_export.py`.
- **1f. Gating + module skeleton** — `app/modules/manufacturing/` mirroring `hr/`; roles `production_manager` / `production_operator` (read) / `tenant_admin`; flag-gated COA seed (WIP, Finished Goods, Material Variance, Manufacturing Overhead, Overhead Applied).

## Phase 2 — Discrete Manufacturing (follow-up)

Builds on the existing inventory item master + stock register.

- **BOM master** (Mongo) — components reference inventory `item_id`s + scrap allowance; operations/work-centres with standard runtime + overhead rate; standard-cost roll-up (1-level explosion in v1).
- **Work Orders** (Mongo) — `draft → released → in_progress → completed → closed`.
  - Material issue: atomic stock decrement via existing stock register → Dr WIP / Cr Raw-Material Inventory, cost-centre tagged.
  - Completion: FG receipt Dr Finished Goods / Cr WIP at standard + Material/Cost Variance line. Deterministic, synchronous, idempotency-keyed (NOT BackgroundTasks).
- **Overhead allocation** (optional) — period-end distribution across cost centres as one balanced multi-line journal.

## Phase 3 — Frontend

Manufacturing workspace in `mitrabooks-erp/app.js`, mirroring HR tabs (ES-module data-attribute delegation, no inline onclick). Tabs: Cost Centres, Budgets, BOMs, Work Orders. Visibility from the never-403 probe.

## Deferred to v2 (noted, not built)

All AI (cost-routing / scrap-prediction / RAG auditing); process/batch manufacturing; multi-level nested BOM explosion; capacity planning; subcontracting; job cards / shop-floor time tracking.

## Cross-cutting

- **Tests:** variance math (over/under/exact + rollback), cost-centre roll-up, budget-vs-actual, gating matrix — mirroring the 60 HR tests.
- **Migration safety:** Phase 1 schema change is one nullable indexed column; zero impact on existing tenants.
- **Deploy:** commit direct to `main`, sync `develop` for Vercel. Backend→Render from `main`, frontend→Vercel from `develop`.
