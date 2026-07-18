# MitraBooks Inventory + Banking Signoff Checklist

Date: 2026-07-18
Scope: MitraBooks ERP inventory (weighted-average periodic) and banking/reconciliation
(bank statement import, BRS, bank/cash book) reporting surfaces.
Environment: hosted staging stack `https://sanmitra-unified-next-staging-sg.onrender.com`
(Path B `ENVIRONMENT=staging` waiver).

## Current State

- Inventory (`app/modules/business/inventory.py`) and banking/reconciliation
  (`app/modules/business/bank_recon.py`, `app/modules/business/banking_books.py`) are
  implemented, tenant/app/entity-scoped, unit-tested, and have passed guarded real-stack
  Playwright mutation coverage. Per `docs/operations/MITRABOOKS_PENDING_GAP_TODO.md`
  (Phase 4) both are `[~]` (implemented; production signoff open) and had no dedicated
  Stage-4/5-style gate until this checklist.
- Bank CSV import now emits a `business_bank_statement_imported` audit event (actor, account,
  provider, parsed/inserted/duplicate counts, batch id) per
  `docs/operations/MITRABOOKS_BANK_FEED_POLICY.md` (previously the import wrote no audit event).

## Target State (Inventory + Banking Gate)

The inventory and banking reporting surfaces can be signed off for production reporting: the
valuation policy is the locked weighted-average periodic method, stock and register reads are
tenant-scoped and free of negative-stock anomalies, the bank/cash book satisfies the
running-balance identity, and inventory/banking routes fail closed for tenants without the
business module.

## Gate Design

Validated by a **read-only** gate (`scripts/mitrabooks_inventory_banking_gate.py`). It performs
login + GET only; never posts, mutates, prints tokens/passwords, or writes secrets. It needs the
demo business credential (and an optional non-business credential for the fail-closed probe) from
a secret manager through the environment.

Authoritative, deterministic signals:

- `GET /api/v1/modules/me` resolves `demo-mitrabooks-business` / `BUSINESS` with modules superset
  `business`/`accounting`/`inventory`.
- `GET /api/v1/business/inventory/policy` returns `valuation_policy == weighted_average_periodic`
  and `policy_locked == true`.
- `GET /api/v1/business/inventory/items`, `.../movements`, `.../closing-stock/entries` return 200
  with the expected shape.
- `GET /api/v1/business/inventory/stock-register` returns 200 with `negative_stock_items` empty
  and a numeric `total_closing_value`.
- `GET /api/v1/business/banking/books?from_date=..&to_date=..&book_type=all` returns 200 and the
  summary satisfies `opening_balance + total_receipts - total_payments == closing_balance`.
- Optional `GET /api/v1/business/bank-recon?account_id=..` returns 200 with a `summary` (skipped
  if no `--bank-account-id`).
- Optional fail-closed probe: with a non-business (HOUSING) credential, the inventory and banking
  routes return 401/403/404.

## Preconditions

1. Valid staging credential for `demo-mitrabooks-business` (from secret manager).
2. Inventory enabled for the demo entity (recommended; policy read works regardless).
3. Optional: a non-business (GruhaMitra) staging credential for the fail-closed probe.
4. Optional: a seeded bank account id for the BRS probe (`--bank-account-id`).

## Smoke Checklist

| Area | Step | Expected Result | Status |
| --- | --- | --- | --- |
| Context | `GET /api/v1/modules/me` | tenant `demo-mitrabooks-business`, org BUSINESS, modules superset business/accounting/inventory | PASS (2026-07-18: BUSINESS; modules accounting/audit/business/gst/inventory) |
| Inventory policy | `GET /api/v1/business/inventory/policy` | 200; `valuation_policy == weighted_average_periodic`; `policy_locked == true` | PASS (2026-07-18: locked weighted-average periodic; `inventory_enabled=false` for the demo entity) |
| Inventory reads | items / movements / closing-stock entries | 200 with expected shape | PASS (2026-07-18: all HTTP 200) |
| Stock register | `GET /api/v1/business/inventory/stock-register` | 200; no negative-stock items; numeric `total_closing_value` | PASS (2026-07-18: HTTP 200; negative_stock_items=0; closing value 0.00 - inventory accounting off) |
| Bank/cash book | `GET /api/v1/business/banking/books?from_date=..&to_date=..&book_type=all` | 200; `opening + receipts - payments == closing` | PASS (2026-07-18: 0.00 + 741200.00 - 153430.00 == 587770.00) |
| Bank recon BRS (optional) | `GET /api/v1/business/bank-recon?account_id=..` | 200 with `summary` (or SKIPPED if no account id) | SKIPPED (2026-07-18: no --bank-account-id supplied) |
| Fail-closed (optional) | inventory + banking routes as a HOUSING tenant | 401/403/404 fail closed (or SKIPPED if no creds) | PASS (2026-07-18: gruhamitra HTTP 403 on stock-register + banking/books) |

## Accounting / Governance Guardrail Checks (Mandatory)

1. Read-only: no account balance or record mutated by this gate (GET requests only).
2. Inventory valuation is the locked weighted-average periodic policy; the financial impact is
   realized only through the period-end closing-stock journal (not verified as mutation here).
3. Bank/cash book totals derive from posted ledger entries and satisfy the running-balance identity.
4. Bank statement CSV import emits the `business_bank_statement_imported` audit event.
5. Routes remain tenant-scoped and fail closed for tenants without the business module.

## Evidence to Capture

- Gate evidence JSON: `tmp/mitrabooks-inventory-banking-evidence.json` (gitignored).
- Per-step status, stock-register negative-count + closing value, bank/cash book identity numbers.
- Any non-2xx status where a 2xx was expected (or vice versa) with endpoint + status code.

## Guarded Command

Read-only; supply credentials from a secret manager (do not paste passwords into docs/chat):

```powershell
$env:MB_INV_BANK_API_BASE_URL = "https://sanmitra-unified-next-staging-sg.onrender.com"
$env:MB_E2E_EMAIL = "<mitrabooks demo admin>"
$env:MB_E2E_PASSWORD = "<from secret manager>"
# Optional fail-closed probe tenant:
$env:GRUHA_E2E_EMAIL = "<gruha demo admin>"
$env:GRUHA_E2E_PASSWORD = "<from secret manager>"
python scripts/mitrabooks_inventory_banking_gate.py --as-of 2026-07-31
# Optional BRS probe for a seeded bank account:
#   python scripts/mitrabooks_inventory_banking_gate.py --as-of 2026-07-31 --bank-account-id <id>
```

Plan/config preview without network calls:

```powershell
python scripts/mitrabooks_inventory_banking_gate.py --dry-run
```

## Exit Criteria

Inventory + banking reporting can be marked ready when:

1. All smoke checklist rows above are PASS (optional rows PASS or SKIPPED with reason).
2. The gate exits PASS with evidence in `tmp/`.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue remains for this surface.
4. Result is recorded in `docs/operations/E2E_VERIFICATION_REPORT.md`.

## Result: PASSED (2026-07-18)

Exit criteria met for the read-only reporting surface:

1. All required smoke checklist rows are PASS; the BRS row is SKIPPED (no bank account id
   supplied) and the fail-closed row is PASS.
2. `scripts/mitrabooks_inventory_banking_gate.py --as-of 2026-07-31` exited PASS; evidence in
   `tmp/mitrabooks-inventory-banking-evidence.json`.
3. No open `[CRITICAL-ACCOUNTING]` or `[CRITICAL-TENANCY]` issue for this surface: the gate is
   read-only, the valuation policy is locked weighted-average periodic, the stock register reports
   0 negative-stock items, the bank/cash book satisfies the running-balance identity, and the
   inventory/banking routes fail closed (HTTP 403) for the non-business HOUSING tenant.
4. Result recorded in `docs/operations/E2E_VERIFICATION_REPORT.md`.

Scope note: the demo business entity has inventory **accounting** disabled
(`inventory_enabled=false`), so the stock register is a trivially empty (0-value, 0-negative)
position. This gate verifies endpoint health, policy lock, no-negative-stock, bank/cash book
correctness, and fail-closed behaviour. A populated inventory valuation signoff (enable inventory
-> post purchases/sales -> closing-stock journal) requires the guarded mutation cycle, which is
already covered by `frontend/e2e/mitrabooks-realstack-destructive.spec.js` and remains deferred as
a scripted variant. Human production/operator signoff also remains a separate manual step.

## Deferred / Non-Goals

- Guarded destructive inventory/banking mutation cycle (item -> movements -> closing-stock journal
  -> reverse; statement import -> match -> unmatch -> bank-only voucher -> reverse) is already
  covered by `frontend/e2e/mitrabooks-realstack-destructive.spec.js`; a scripted guarded variant of
  this gate can be added later if a repeatable write cycle is wanted.
- Multi-location / batch / serial inventory controls and live bank-feed provider sync remain
  explicitly deferred (see `MITRABOOKS_BANK_FEED_POLICY.md` and the gap matrix).
- Human production/operator signoff (review of stock valuation and BRS outcomes) is out of scope
  for this automated gate and remains a manual step.
