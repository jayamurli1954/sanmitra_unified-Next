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

Staging mode is read-only by default. Destructive deployed browser mutation is allowed only after the guarded demo policy check passes.

Demo credential setup is documented in `docs/operations/MITRABOOKS_ERP_DEMO_CREDENTIALS.md`. The operator-facing demo admin email is `business.admin@sanmitra.local`; the password must remain a staging/runtime secret.

## Destructive Demo Tenant Policy

The approved destructive browser target is the MitraBooks business demo tenant only:

| Field | Required value |
| --- | --- |
| Tenant id | `demo-mitrabooks-business` |
| App key | `mitrabooks` |
| Organization type | `BUSINESS` |
| Demo modules | `business`, `accounting`, `gst`, `inventory`, `audit` |
| Admin bootstrap | `DEMO_MITRABOOKS_BOOTSTRAP=true` with a staging-only `DEMO_MITRABOOKS_ADMIN_PASSWORD` |
| E2E seed | `DEMO_MITRABOOKS_E2E_SEED_ENABLED=true` or an operator-run demo seed before mutation |

Reset policy:

1. Never run create/post/reverse browser tests against a real customer, trust, housing society, CA practice, or production tenant.
2. Before a destructive deployed run, reset or reseed `demo-mitrabooks-business` with the MitraBooks demo seed path and confirm the login belongs to that tenant.
3. After a destructive deployed run, reseed the same demo tenant or discard the staging database snapshot so generated vouchers, invoices, bills, notes, and reversals do not become baseline data.
4. Keep demo credentials in deployment/runtime secrets only; do not commit them or print them in reports.

Policy check:

```powershell
$env:MITRABOOKS_DEMO_E2E_CONFIRM="demo-mitrabooks-business"
$env:E2E_USER_EMAIL="<staging demo admin email>"
$env:E2E_USER_PASSWORD="<staging demo password>"
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --destructive-demo-policy-check --demo-tenant-id demo-mitrabooks-business
```

This command validates the destructive deployed mutation preconditions. It does not execute destructive mutation by itself.

After the demo tenant has been reset/reseeded and the policy check is green, run the destructive real-stack browser/API mutation gate explicitly:

```powershell
$env:MITRABOOKS_DEMO_E2E_CONFIRM="demo-mitrabooks-business"
$env:E2E_USER_EMAIL="<staging demo admin email>"
$env:E2E_USER_PASSWORD="<staging demo password>"
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --run-destructive-demo --demo-tenant-id demo-mitrabooks-business
```

This executes `frontend/e2e/mitrabooks-realstack-destructive.spec.js`, which signs in through the browser, confirms the tenant context is `demo-mitrabooks-business`, creates/reviews/posts the core business documents through the real backend, verifies accounting report availability, and reverses/cancels the generated documents.

## Validation Matrix

| Gate area | Evidence | Current status |
| --- | --- | --- |
| Parties | Backend service tests and browser workflow smoke | Passed on 2026-07-02 |
| Vouchers | Backend API smoke, approval/reversal tests, browser create/reverse smoke | Passed on 2026-07-02 |
| Sales invoices | Backend posting/approval/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Sales invoice deep E2E/API hardening | Real accounting service test for create -> approve/post -> AR/revenue/GST journal lines -> trial balance -> customer statement -> PDF/export artifact -> cancel/reverse -> reversal journal -> zero receivable -> tenant denial | Passed on 2026-07-03 |
| Purchase bills | Backend posting/approval/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Purchase bill deep E2E/API hardening | Real accounting service test for create -> approve/post -> expense/input GST/AP journal lines -> trial balance -> vendor statement/export -> Rule 37 ITC preview/reversal/reclaim -> payment marking -> cancel/reverse -> reversal journal -> zero payable -> tenant denial | Passed on 2026-07-03 |
| Credit notes | Backend posting/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Credit note deep E2E/API hardening | Real accounting service test for source invoice -> create linked credit note -> approve/post -> revenue/output GST debit and AR credit journal lines -> trial balance -> customer statement/export -> cancel/reverse -> reversal journal -> restored receivable -> tenant denial | Passed on 2026-07-03 |
| Debit notes | Backend posting/cancel tests and browser create/detail/reverse smoke | Passed on 2026-07-02 |
| Reports and drill-down | Accounting report tests, party sub-ledger tests, ERP accounting panel smoke | Passed on 2026-07-02 |
| Print/export guards | Report export and invoice/bill PDF guard tests | Passed on 2026-07-02 |
| Staging shell | Optional read-only deployed shell smoke | Passed on 2026-07-02 against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |
| Local real-stack mutation | Guarded browser/API mutation against local `demo-mitrabooks-business` | Passed on 2026-07-03 against `http://127.0.0.1:3300/mitrabooks-erp/` |
| Hosted staging real-stack mutation | Guarded browser/API mutation against hosted `demo-mitrabooks-business` | Passed on 2026-07-03 against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/` |

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
- PASS: destructive deployed mutation policy is now defined and guarded for `demo-mitrabooks-business`; actual mutation remains an explicit operator action after demo credentials and reset are present.
- ADDED: guarded destructive real-stack Playwright runner for the demo tenant; not executed until staging credentials and reset/reseed are present.

This closes the Phase 3 core workflow signoff gate for local backend/API proof, local/deployed shell browser proof, and the previously missing demo tenant/reset policy. Destructive deployed mutation remains intentionally opt-in and must not run unless the guarded demo-policy check passes.

2026-07-03:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url http://127.0.0.1:3300/mitrabooks-erp/ --run-destructive-demo --demo-tenant-id demo-mitrabooks-business
```

Result:

- PASS: backend business workflow pytest group, 131 tests.
- PASS: frontend business contract pytest group, 30 tests.
- PASS: local Playwright MitraBooks shell workflow smoke, 3 checks.
- PASS: read-only MitraBooks shell smoke against `http://127.0.0.1:3300/mitrabooks-erp/`, 3 checks.
- PASS: destructive demo policy for `demo-mitrabooks-business`.
- PASS: destructive local real-stack browser/API mutation. The E2E signed in as the MitraBooks demo admin, created a customer and vendor party, posted a voucher, sales invoice, purchase bill, credit note, and debit note, verified accounting report availability, and reversed/cancelled the generated financial documents.

2026-07-03:

```powershell
python scripts/mitrabooks_phase3_business_gate.py --staging-url https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/ --run-destructive-demo --demo-tenant-id demo-mitrabooks-business
```

Result:

- PASS: backend business workflow pytest group, 131 tests.
- PASS: frontend business contract pytest group, 30 tests.
- PASS: local Playwright MitraBooks shell workflow smoke, 3 checks.
- PASS: read-only hosted MitraBooks shell smoke against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`, 3 checks.
- PASS: destructive demo policy for `demo-mitrabooks-business`.
- PASS: destructive hosted staging real-stack browser/API mutation. The E2E signed in as the MitraBooks demo admin, created a customer and vendor party, posted a voucher, sales invoice, purchase bill, credit note, and debit note, verified accounting report availability, and reversed/cancelled the generated financial documents.

2026-07-03:

```powershell
python -m pytest tests/test_business_phase2.py::test_sales_invoice_deep_e2e_posts_reports_exports_and_reverses -q
python -m pytest tests/test_business_phase2.py -q
```

Result:

- PASS: focused Sales Invoice deep E2E/API hardening test.
- PASS: full `tests/test_business_phase2.py` suite, 66 tests.
- The Sales Invoice deep test uses the real accounting service and test database for posting, trial balance, voucher detail, party sub-ledger statement, reversal, outstanding balance, and tenant-denial checks. Mongo-backed business document storage and dunning log reads are faked in-memory for deterministic local execution.
- The test creates a customer-scoped GST sales invoice, approves/posts it, verifies debit receivable and credit revenue/CGST/SGST lines, checks trial balance and customer statement effects, builds a sales-invoice PDF and CSV export artifact, cancels the invoice, verifies reversal lines and zero receivable outstanding, and confirms cross-tenant voucher access is denied.

2026-07-03:

```powershell
python -m pytest tests/test_business_phase2.py::test_purchase_bill_deep_e2e_posts_reports_payment_itc_and_reverses -q
python -m pytest tests/test_business_phase2.py -q
```

Result:

- PASS: focused Purchase Bill deep E2E/API hardening test.
- PASS: full `tests/test_business_phase2.py` suite, 67 tests.
- The Purchase Bill deep test uses the real accounting service and test database for posting, trial balance, voucher detail, party sub-ledger statement, ITC reversal/reclaim journals, reversal, outstanding balance, and tenant-denial checks. Mongo-backed business document storage and dunning log reads are faked in-memory for deterministic local execution.
- The test creates a vendor-scoped GST purchase bill, approves/posts it, verifies debit expense/input CGST/input SGST and credit AP lines, checks trial balance and vendor statement/export effects, previews Rule 37 ITC reversal, posts ITC reversal with interest, marks the bill paid, reclaims ITC, cancels the purchase bill, verifies reversal lines and zero payable outstanding, and confirms cross-tenant voucher access is denied.

2026-07-03:

```powershell
python -m pytest tests/test_business_phase2.py::test_credit_note_deep_e2e_posts_reports_exports_and_reverses -q
```

Result:

- PASS: focused Credit Note deep E2E/API hardening test.
- The Credit Note deep test uses the real accounting service and test database for source invoice posting, credit note posting, trial balance, voucher detail, party sub-ledger statement, reversal, outstanding balance, and tenant-denial checks. Mongo-backed business document storage and dunning log reads are faked in-memory for deterministic local execution.
- The test creates a customer-scoped GST sales invoice, approves/posts it, creates a linked GST credit note against the source invoice, verifies debit revenue/output CGST/output SGST and credit receivable lines, checks trial balance and customer statement/export effects, cancels the credit note, verifies reversal lines and restored receivable outstanding, and confirms cross-tenant voucher access is denied.

## Remaining Gaps After This Gate

- Local demo database cleanup may still be needed if the local tenant must return to a clean baseline; the destructive E2E reverses/cancels generated financial documents, but generated test parties may remain.
- Hosted staging demo database cleanup may still be needed if the hosted tenant must return to a clean baseline; the destructive E2E reverses/cancels generated financial documents, but generated test parties may remain.
- Debit Note deep hardening remains the next Phase 3 sub-gate: source document linkage, posting impact, statement/report effects, cancel/reverse, and tenant denial.
- Credit Note browser source-document enforcement and dedicated print/export polish remain open for later production signoff; API/accounting/report/reversal depth is closed for the local gate.
- Compliance signoff is still required for GST/TDS/GSTR/e-invoice/e-way bill positioning.
- Approval depth still needs production operator review across tenant settings, year-end, GST settlement, and sensitive exports.
- Print/PDF templates need visual signoff for numbering, signatures, branding, and export governance.
- Bank reconciliation, inventory, fixed assets, CA practice operations, and data-health/MIS need separate Phase 3-4 sub-gates.
- Live GST/e-way bill APIs, bank execution, OCR/AI auto-posting, AI MIS, advanced inventory depth, full export governance, and mobile apps remain deferred.

## Non-Goals

- Do not run destructive staging actions on real tenant data.
- Do not treat mocked browser smoke as proof that production backend credentials, demo seed data, and rollback policy are complete.
- Do not include InvestMitra in unified SanMitra ERP scope.
