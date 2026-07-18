# MitraBooks Stage 5 Combined ERP Regression Checklist

Date: 2026-07-18
Scope: MitraBooks, MandirMitra, and GruhaMitra coexistence in the unified MitraBooks ERP shell
Environment: hosted staging stack `https://sanmitra-unified-next-staging-sg.onrender.com` (Path B `ENVIRONMENT=staging` waiver)

## Current State

- Stage 5 starts after MandirMitra Stage 3 machine signoff PASS (`backend-v1.3.0`) and GruhaMitra Stage 4 CLOSED (hosted billing-to-accounting PASS on 2026-07-17).
- Demo tenants used for combined regression:
  - MitraBooks: `demo-mitrabooks-business` (`organization_type=BUSINESS`, modules `business`/`accounting`/`audit`), app key `mitrabooks`.
  - MandirMitra: `demo-mandir-tenant` (`organization_type=TEMPLE`, modules `temple`/`accounting`/`audit`), app key `mandirmitra`.
  - GruhaMitra: `gruhamitra-demo-society` (`organization_type=HOUSING`, modules `housing`/`accounting`/`audit`), app key `gruhamitra`.
- Prior single-product mixed postings already exist (Mandir Stage 3 destructive 8/8; Gruha Stage 4 journals 427-437), so Stage 5 verifies that reports remain correct after those mixed workflow postings.

## Target State (Stage 5 Gate)

The unified ERP can be maintained as one product surface: enabled modules and permissions
drive access, product names are not used as access rules, app context does not leak across
tenants, module-specific routes fail closed when a module is disabled, and accounting reports
stay correct and tenant-scoped after mixed workflow postings.

## Gate Design

Stage 5 is validated by a **read-only** gate (`scripts/mitrabooks_stage5_combined_regression_gate.py`).
It only performs login + GET requests. It never posts, mutates, or prints tokens/passwords.
No destructive-confirmation env vars are required; the gate needs only staging credentials for
each demo tenant, supplied from a secret manager through the runtime environment.

Authoritative, deterministic signals (aligned with `app/core/modules/registry.py`):

- `GET /api/v1/modules/me` resolves the expected `tenant_id`, `organization_type`, and enabled
  module keys per tenant (access driven by module key, not by product name).
- `GET /api/v1/accounting/reports/trial-balance` returns HTTP 200 and `balanced == true`
  (`total_debit == total_credit`) for each tenant, tenant-scoped.
- `GET /api/v1/business/parties` is guarded by `require_enabled_module("business")`:
  - BUSINESS tenant -> 2xx (module enabled, positive access).
  - TEMPLE and HOUSING tenants -> 401/403/404 (fail closed, module disabled).
- Cross-tenant isolation: each demo tenant resolves a distinct `tenant_id` (no shared/leaked context).

## Preconditions

1. Valid staging credentials exist for each of the three demo tenants (from secret manager).
2. Each tenant has its expected `organization_type` and modules enabled.
3. Prior stage postings exist so trial balances are non-trivial (optional but recommended).

## Smoke Checklist

| Area | Step | Expected Result | Status |
| --- | --- | --- | --- |
| Enabled modules drive access | `GET /api/v1/modules/me` for all three tenants | Correct `tenant_id` + `organization_type` + module keys per registry | PASS (2026-07-18: BUSINESS=accounting/audit/business/gst/inventory, TEMPLE=accounting/audit/temple, HOUSING=accounting/audit/housing) |
| Product names not hardcoded | Access decisions compared by module key, not product name | BUSINESS/TEMPLE/HOUSING resolve by module, not by app name string | PASS (gate asserts by module key) |
| App context no leak | Each demo tenant resolves only its own tenant context | Three distinct `tenant_id` values; no shared context | PASS (2026-07-18: 3 distinct tenants resolved) |
| Accounting after mixed postings (MitraBooks) | `GET .../trial-balance` for `demo-mitrabooks-business` | HTTP 200; `balanced == true` | PASS (2026-07-18: 1,636,082.00 == 1,636,082.00) |
| Accounting after mixed postings (MandirMitra) | `GET .../trial-balance` for `demo-mandir-tenant` | HTTP 200; `balanced == true` | PASS (2026-07-18: 1,149,320.91 == 1,149,320.91) |
| Accounting after mixed postings (GruhaMitra) | `GET .../trial-balance` for `gruhamitra-demo-society` | HTTP 200; `balanced == true` | PASS (2026-07-18: 439,927.01 == 439,927.01) |
| Module route positive access | `GET /api/v1/business/parties` as BUSINESS tenant | 2xx (business module enabled) | PASS (2026-07-18: HTTP 200) |
| Module route fail-closed (TEMPLE) | `GET /api/v1/business/parties` as TEMPLE tenant | 401/403/404 fail closed | PASS (2026-07-18: HTTP 403) |
| Module route fail-closed (HOUSING) | `GET /api/v1/business/parties` as HOUSING tenant | 401/403/404 fail closed | PASS (2026-07-18: HTTP 403) |

## Accounting Guardrail Checks (Mandatory)

1. Trial balance for each tenant is balanced (`total_debit == total_credit`).
2. No account balance is mutated by this gate (read-only; GET requests only).
3. Reports remain tenant-scoped; one tenant's postings do not appear in another's totals.

## Evidence to Capture

- Gate evidence JSON: `tmp/mitrabooks-stage5-combined-regression-evidence.json` (gitignored).
- Per-tenant `modules/me` context, trial-balance totals, and the module fail-closed matrix.
- Any non-2xx status where a 2xx was expected (or vice versa) with endpoint + status code.

## Guarded Command

Read-only; supply credentials from a secret manager (do not paste passwords into docs/chat):

```powershell
$env:STAGE5_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:MB_E2E_EMAIL = "<mitrabooks demo admin>"
$env:MB_E2E_PASSWORD = "<from secret manager>"
$env:MANDIR_E2E_EMAIL = "<mandir demo admin>"
$env:MANDIR_E2E_PASSWORD = "<from secret manager>"
$env:GRUHA_E2E_EMAIL = "<gruha demo admin>"
$env:GRUHA_E2E_PASSWORD = "<from secret manager>"
python scripts/mitrabooks_stage5_combined_regression_gate.py --as-of 2026-07-31
```

Plan/config preview without network calls:

```powershell
python scripts/mitrabooks_stage5_combined_regression_gate.py --dry-run
```

Demo emails exist in the per-product user guides / Track 0 runbooks. Prefer secret manager for staging.

## Exit Criteria for Stage 5

Stage 5 can be marked ready when:

1. All smoke checklist rows above are PASS.
2. The combined-regression gate exits PASS with evidence in `tmp/`.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue remains.
4. Result is recorded in `docs/operations/E2E_VERIFICATION_REPORT.md` under a Stage 5 section.

## Stage 5 Result: PASSED (2026-07-18)

All exit criteria are met:

1. All smoke checklist rows are PASS.
2. `scripts/mitrabooks_stage5_combined_regression_gate.py --as-of 2026-07-31` exited PASS for all
   three demo tenants plus cross-tenant isolation; evidence in
   `tmp/mitrabooks-stage5-combined-regression-evidence.json`.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue remains: each tenant's trial
   balance is balanced and tenant-scoped, the `require_enabled_module("business")` route failed
   closed (HTTP 403) for TEMPLE/HOUSING and succeeded (HTTP 200) for BUSINESS, and the three
   tenants resolved distinct contexts.
4. Result recorded in `docs/operations/E2E_VERIFICATION_REPORT.md` (Stage 5 section).

Environment note: the combined regression ran read-only against the hosted staging stack
(`https://sanmitra-unified-next-staging-sg.onrender.com`, Path B `ENVIRONMENT=staging` waiver).

Ops note: during Stage 5 prep the staging GruhaMitra demo login was reseeded and, separately,
the exposed Atlas connection credential was rotated and `MONGODB_URI` updated in Render staging.
No repository secret was involved; both are operator-side staging changes.

## Deferred / Non-Goals

- No new destructive postings are required to close Stage 5; it verifies coexistence and
  correctness after the already-completed Stage 3/4 postings. An optional destructive
  mixed-posting variant can be added later if a fresh combined posting cycle is wanted.
- Full frontend merge, InvestMitra (unified exclusion), and broad MitraBooks business ERP
  expansion remain out of scope for this gate.
