# MitraBooks Phase 5 MIS / Data-Health / Export Signoff Checklist

Date: 2026-07-18
Scope: MitraBooks ERP Phase 5 reporting surfaces - MIS KPI contracts, Financial Health,
Data Health Score, export governance (JSON/CSV/XLSX/PDF), and Tally XML export.
Environment: hosted staging stack `https://sanmitra-unified-next-staging-sg.onrender.com`
(Path B `ENVIRONMENT=staging` waiver).

## Current State

- MIS KPIs (`app/modules/business/mis.py`), Financial Health
  (`app/modules/business/financial_health.py`), Data Health Score
  (`app/modules/business/data_health.py`), export governance
  (`app/modules/business/export_governance.py` + `report_export.py`), and Tally XML
  (`app/modules/business/tally_xml.py`) are implemented, deterministic, tenant-scoped,
  and ledger-backed, with unit + route-contract + guarded real-stack Playwright coverage.
- Per `docs/operations/MITRABOOKS_PENDING_GAP_TODO.md` (Phase 5 Open Gaps), all five items
  are `[~]` (implemented; production report/compliance signoff still open) and there was no
  dedicated Stage-4/5-style signoff gate for this surface until this checklist.

## Target State (Phase 5 Gate)

The Phase 5 reporting surface can be signed off for production reporting: every KPI, health
score, and export is deterministic and source-backed, export downloads are role-governed and
audited, Tally XML is a governed data-portability artifact, and all of these routes fail closed
for tenants without the business module.

## Gate Design

Phase 5 is validated by a **read-only** gate
(`scripts/mitrabooks_phase5_mis_datahealth_export_gate.py`). It performs login + GET only. It
never posts, mutates, prints tokens/passwords, or writes secrets. No destructive-confirmation
env vars are required; it needs only the demo business credential (and an optional non-business
credential for the fail-closed probe), supplied from a secret manager through the environment.

Authoritative, deterministic signals (aligned with the module contracts and
`app/modules/business/export_governance.py`):

- `GET /api/v1/modules/me` resolves `tenant_id=demo-mitrabooks-business`,
  `organization_type=BUSINESS`, modules superset of `business`/`accounting`/`audit`.
- `GET /api/v1/business/mis/kpis` returns a `source` provenance map plus
  `monthly_sales_purchase_trend`, `top_customers`, `working_capital`, `overdue`.
- `GET /api/v1/business/financial-health?narrate=false` returns `summary`/`kpis`/`charts`/
  `alerts` with `narrative == null` (AI narration OFF, deterministic).
- `GET /api/v1/business/data-health` returns numeric `score`, `grade`, `status`
  (`ready`/`needs_attention`), non-empty `rules`, and an `issues` list whose entries carry
  `issue_id` + `workspace` + `action_label`.
- `GET /api/v1/business/reports/export?report=trial_balance&format={json,csv,xlsx,pdf}`
  returns HTTP 200 with governed headers `X-SanMitra-Export-Governed: true`,
  `X-SanMitra-Export-Type: business_report`, `X-SanMitra-Export-Format: <format>`.
- `GET /api/v1/business/tally/xml-export` returns governed `application/xml` containing the
  `All Masters` ledger-master envelope and `SANMITRAEXPORT` source metadata.
- Optional fail-closed probe: with a non-business (HOUSING) credential, the Phase 5 routes
  return 401/403/404 (module fails closed).

## Preconditions

1. Valid staging credential for `demo-mitrabooks-business` (from secret manager).
2. The tenant has posted data so KPIs/reports are non-trivial (recommended; Stage 5 postings suffice).
3. Optional: a non-business (e.g. GruhaMitra) staging credential for the fail-closed probe.
4. If staging cannot render PDF, run with `--formats json,csv,xlsx`.

## Smoke Checklist

| Area | Step | Expected Result | Status |
| --- | --- | --- | --- |
| Context | `GET /api/v1/modules/me` | tenant `demo-mitrabooks-business`, org BUSINESS, modules superset business/accounting/audit | PASS (2026-07-18: BUSINESS; modules accounting/audit/business/gst/inventory) |
| MIS KPIs | `GET /api/v1/business/mis/kpis` | 200; `source` map + trend/top_customers/working_capital/overdue present | PASS (2026-07-18: HTTP 200, source-backed, current_ratio present) |
| Financial Health | `GET /api/v1/business/financial-health?narrate=false` | 200; summary/kpis/charts/alerts present; `narrative == null` | PASS (2026-07-18: HTTP 200, narrative off) |
| Data Health | `GET /api/v1/business/data-health` | 200; numeric score, grade, status in {ready,needs_attention}, rules non-empty, issues carry issue_id/workspace/action_label | PASS (2026-07-18: HTTP 200, score 100, grade A, status ready, 5 rules, 0 issues) |
| Export governance (JSON) | `GET .../reports/export?report=trial_balance&format=json` | 200; `X-SanMitra-Export-Governed: true` + type/format headers | PASS (2026-07-18: HTTP 200, governed) |
| Export governance (CSV) | `...&format=csv` | 200; governed headers, format=csv | PASS (2026-07-18: HTTP 200, governed) |
| Export governance (XLSX) | `...&format=xlsx` | 200; governed headers, format=xlsx | PASS (2026-07-18: HTTP 200, governed) |
| Export governance (PDF) | `...&format=pdf` | 200; governed headers, format=pdf | PASS (2026-07-18: HTTP 200, governed) |
| Tally XML | `GET /api/v1/business/tally/xml-export` | 200; application/xml; governed; contains `All Masters` + `SANMITRAEXPORT` | PASS (2026-07-18: HTTP 200, application/xml, governed, masters + source metadata) |
| Fail-closed (optional) | Phase 5 routes as a HOUSING tenant | 401/403/404 fail closed (or SKIPPED if no creds) | PASS (2026-07-18: gruhamitra HTTP 403 on mis/kpis + data-health) |

## Accounting / Governance Guardrail Checks (Mandatory)

1. Read-only: no account balance or record is mutated by this gate (GET requests only).
2. Every KPI/health/export figure is deterministic and source-backed (no inference, no AI numbers).
3. Every export download is role-governed and emits the `business_export_downloaded` audit event.
4. Routes remain tenant-scoped and fail closed for tenants without the business module.

## Evidence to Capture

- Gate evidence JSON: `tmp/mitrabooks-phase5-mis-datahealth-export-evidence.json` (gitignored).
- Per-step status, export governed-header matrix per format, and the Tally XML marker checks.
- Any non-2xx status where a 2xx was expected (or vice versa) with endpoint + status code.

## Guarded Command

Read-only; supply credentials from a secret manager (do not paste passwords into docs/chat):

```powershell
$env:MB_PHASE5_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:MB_E2E_EMAIL = "<mitrabooks demo admin>"
$env:MB_E2E_PASSWORD = "<from secret manager>"
# Optional fail-closed probe tenant:
$env:GRUHA_E2E_EMAIL = "<gruha demo admin>"
$env:GRUHA_E2E_PASSWORD = "<from secret manager>"
python scripts/mitrabooks_phase5_mis_datahealth_export_gate.py --as-of 2026-07-31
```

Plan/config preview without network calls:

```powershell
python scripts/mitrabooks_phase5_mis_datahealth_export_gate.py --dry-run
```

## Exit Criteria for Phase 5 Reporting Signoff

Phase 5 reporting can be marked ready when:

1. All smoke checklist rows above are PASS (fail-closed row PASS or SKIPPED with reason).
2. The gate exits PASS with evidence in `tmp/`.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue remains for this surface.
4. Result is recorded in `docs/operations/E2E_VERIFICATION_REPORT.md`.

## Phase 5 Result: PASSED (2026-07-18)

All exit criteria are met:

1. All smoke checklist rows are PASS (fail-closed row PASS - not skipped).
2. `scripts/mitrabooks_phase5_mis_datahealth_export_gate.py --as-of 2026-07-31` exited PASS for
   all seven steps; evidence in `tmp/mitrabooks-phase5-mis-datahealth-export-evidence.json`.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue remains for this surface: the
   gate is read-only (no mutation), every KPI/health/export figure is source-backed and
   deterministic (financial-health `narrative == null` with AI off; data-health score 100/grade A),
   all four export formats returned governed headers, Tally XML returned the governed
   `All Masters` envelope with `SANMITRAEXPORT` metadata, and the Phase 5 routes failed closed
   (HTTP 403) for the non-business HOUSING tenant.
4. Result recorded in `docs/operations/E2E_VERIFICATION_REPORT.md`.

Environment note: the gate ran read-only against the hosted staging stack
(`https://sanmitra-unified-next-staging-sg.onrender.com`, Path B `ENVIRONMENT=staging` waiver).

Automated-scope note: this gate closes the machine-verifiable Phase 5 reporting signals. Human
production/compliance report signoff, voucher-level Tally XML, AI MIS narration, wider GST-JSON
export governance, persisted data-health assignee/status workflow, and duplicate-invoice guarded
real-stack evidence remain open and are tracked separately (see Deferred / Non-Goals).

## Deferred / Non-Goals

- Voucher-level Tally XML, real Tally import validation, and a Tally migration runbook remain a
  separate feature/ops effort (trial-balance ledger-master XML is a data-portability proof only).
- AI MIS narration enablement, wider GST-JSON export governance, persisted data-health
  assignee/status workflow, and duplicate-invoice guarded real-stack evidence remain open and are
  tracked separately in the pending-gap tracker.
- Human production/compliance report signoff (operator review) is out of scope for this
  automated gate and remains a manual step.
