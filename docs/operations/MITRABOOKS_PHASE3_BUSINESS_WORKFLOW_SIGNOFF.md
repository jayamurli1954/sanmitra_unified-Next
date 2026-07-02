# MitraBooks Phase 3 Business Workflow Signoff

## Purpose

This gate starts Phase 3-4 production hardening with the core MitraBooks business cycle:

```text
party -> voucher -> sales invoice -> purchase bill -> credit note -> debit note -> report/drill-down -> reverse/cancel
```

It is a signoff gate for the currently implemented business workflow foundation. It is not a declaration that every Phase 3-4 advanced workflow, compliance integration, or production mutation test is complete.

## Current State

- Backend slices exist for parties, typed vouchers, sales invoices, purchase bills, credit notes, debit notes, statements, reports, PDF/export guards, payment allocation, and party sub-ledgers.
- Backend tests cover posting, approval, reversal/cancellation, compensation when persistence fails, tenant/app scoping, route contracts, and accounting report drill-down.
- Browser coverage exists for the MitraBooks ERP shell with mocked API responses. It covers create/post/detail/reverse surfaces for parties, vouchers, invoices, bills, credit notes, and debit notes.
- Phase 2E staging read-only shell validation passed against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`.

## Target State

Phase 3 core workflow signoff requires:

- Real backend/API tests pass for core business workflow posting, reports, and reversal.
- Browser workflow smoke passes for the MitraBooks ERP shell.
- Route contracts stay aligned between frontend and backend.
- Report and export paths prove they read posted/accounting-safe records.
- Remaining production gaps are explicitly documented instead of hidden under a "complete" label.

## Repeatable Gate

Run:

```powershell
python scripts/mitrabooks_phase3_business_gate.py
```

This runs:

- `tests/test_business_phase2.py`
- `tests/test_mitrabooks_erp_core_smoke.py`
- route/report/sub-ledger/payment-allocation/statement/export/PDF focused tests
- frontend contract tests
- local Playwright MitraBooks shell workflow smoke

For read-only deployed shell validation, run:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

Staging mode is read-only. Destructive staging tests need a clearly marked business demo tenant, seed data, and reset policy.

## Validation Matrix

| Gate area | Evidence | Current status |
| --- | --- | --- |
| Parties | Backend service tests and browser workflow smoke | Passed on 2026-07-02 |
| Vouchers | Backend API smoke, approval/reversal tests, browser create/reverse smoke | Passed on 2026-07-02 |
| Sales invoices | Backend posting/approval/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Purchase bills | Backend posting/approval/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Credit notes | Backend posting/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Debit notes | Backend posting/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Reports and drill-down | Accounting report tests, party sub-ledger tests, ERP accounting panel smoke | Passed on 2026-07-02 |
| Print/export guards | Report export and invoice/bill PDF guard tests | Passed on 2026-07-02 |
| Staging shell | Optional read-only deployed shell smoke | Passed on 2026-07-02 against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |

## Latest Run

2026-07-02:

```powershell
python scripts/mitrabooks_phase3_business_gate.py
```

Result:

- PASS: backend business workflow pytest group, 131 tests.
- PASS: frontend business contract pytest group, 30 tests.
- PASS: local Playwright MitraBooks shell workflow smoke, 3 checks.
- SKIPPED: staging shell smoke because no staging URL was supplied for this local-only run.

2026-07-02:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/
```

Result:

- PASS: backend business workflow pytest group, 131 tests.
- PASS: frontend business contract pytest group, 30 tests.
- PASS: local Playwright MitraBooks shell workflow smoke, 3 checks.
- PASS: read-only staging MitraBooks ERP shell smoke, 3 checks.

This closes the Phase 3 core workflow signoff gate for local backend/API proof plus local/deployed shell browser proof. It does not close destructive deployed mutation testing.

## Remaining Gaps After This Gate

- Real-stack browser mutation against a deployed backend still requires a safe business demo tenant and reset policy.
- Compliance signoff is still required for GST/TDS/GSTR/e-invoice/e-way bill positioning.
- Approval depth still needs production operator review across tenant settings, year-end, GST settlement, and sensitive exports.
- Print/PDF templates need visual signoff for numbering, signatures, branding, and export governance.
- Bank reconciliation, inventory, fixed assets, CA practice operations, and data-health/MIS need separate Phase 3-4 sub-gates.
- Live GST/e-way bill APIs, bank execution, OCR/AI auto-posting, AI MIS, advanced inventory depth, full export governance, and mobile apps remain deferred.

## Non-Goals

- Do not run destructive staging actions on real tenant data.
- Do not treat mocked browser smoke as proof that production backend credentials, demo seed data, and rollback policy are complete.
- Do not include InvestMitra in unified SanMitra ERP scope.
