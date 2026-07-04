# MitraBooks Pending Gap Todo

## Purpose

This is the living completion tracker for MitraBooks ERP and the SanMitra unified ERP path. Use this file to mark completed work with strikethrough while keeping pending gaps visible.

Status convention:

- `~~[x] Completed item~~` means the task is closed and evidence is recorded.
- `[ ] Pending item` means the task is still open.
- `[~] In progress / partially closed` means implementation exists but production signoff is not complete.

## Closed Baseline

- ~~[x] Phase 1 local closeout: accounting compensation patterns, invoice/bill lifecycle, posted-only invoice output guard, CA invite hardening, and local frontend preflight evidence recorded.~~
- ~~[x] Phase 2A: pricing/catalog/Razorpay metadata direction implemented locally.~~
- ~~[x] Phase 2B: core business settings backend contracts implemented locally.~~
- ~~[x] Phase 2C: CA practice client master, document queue, work assignment, and company switching implemented locally.~~
- ~~[x] Phase 2D: review-first integration, document storage, OCR, AI, GST, bank, WhatsApp, and email configuration shells implemented locally; live provider execution remains deferred.~~
- ~~[x] Phase 2E: local validation, accounting guardrail checks, tenant/app isolation checks, and read-only staging shell smoke closed for the planned validation scope.~~
- ~~[x] Phase 3 core workflow gate foundation: backend/API tests, frontend contract tests, local browser shell smoke, read-only deployed shell smoke, and guarded destructive demo-tenant policy recorded.~~
- ~~[x] Phase 3 destructive real-stack runner added: `frontend/e2e/mitrabooks-realstack-destructive.spec.js` and `--run-destructive-demo` gate support are available but intentionally opt-in.~~
- ~~[x] Phase 3 local destructive real-stack demo mutation passed on 2026-07-03 against `http://127.0.0.1:3300/mitrabooks-erp/`: party -> voucher -> sales invoice -> purchase bill -> credit note -> debit note -> report/drill-down -> reverse/cancel.~~
- ~~[x] Phase 3 hosted staging destructive real-stack demo mutation passed on 2026-07-03 against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`: party -> voucher -> sales invoice -> purchase bill -> credit note -> debit note -> report/drill-down -> reverse/cancel.~~
- ~~[x] Phase 3 Sales Invoice deep API/E2E hardening passed locally on 2026-07-03: create customer-scoped sales invoice -> approve/post -> verify AR/revenue/GST journal lines -> trial balance -> customer statement -> PDF/export artifact -> cancel/reverse -> reversal journal -> zero receivable -> tenant denial.~~
- ~~[x] Phase 3 Purchase Bill deep API/E2E hardening passed locally on 2026-07-03: create vendor-scoped purchase bill -> approve/post -> verify expense/input GST/AP journal lines -> trial balance -> vendor statement/export -> Rule 37 ITC preview/reversal/reclaim -> payment marking -> cancel/reverse -> reversal journal -> zero payable -> tenant denial.~~
- ~~[x] Phase 3 Credit Note deep API/E2E hardening passed locally on 2026-07-03: create customer invoice source -> create credit note linked to source invoice -> approve/post -> verify revenue/output GST debit and AR credit journal lines -> trial balance -> customer statement/export -> cancel/reverse -> reversal journal -> restored receivable -> tenant denial.~~
- ~~[x] Phase 3 Debit Note deep API/E2E hardening passed locally on 2026-07-03: create vendor bill source -> create debit note linked to source bill -> approve/post -> verify AP debit and expense/input GST credit journal lines -> trial balance -> vendor statement/export -> cancel/reverse -> reversal journal -> restored payable -> tenant denial.~~
- ~~[x] Phase 3 Receivables browser E2E shell hardening passed locally on 2026-07-03: party-ledger receivables/payables tab -> AR/AP ageing kind switch -> receipt allocation FIFO/open-item match -> reconciliation status -> customer statement -> dunning reminder record.~~
- ~~[x] Phase 3 Payables browser E2E shell hardening passed locally on 2026-07-03: vendor statement -> payable allocation FIFO/open-item match -> reconciliation status -> Rule 37 ITC bill-payment marking -> TDS register vendor evidence.~~
- ~~[x] Phase 3 GST/TDS compliance browser shell slice passed locally on 2026-07-03: tenant GST profile evidence -> GST settlement preview/post with period lock -> GSTR-3B summary -> GSTR-1 outward/HSN evidence -> TDS section/register evidence -> manual period lock/unlock.~~
- ~~[x] Phase 3 GST/TDS real-stack compliance browser/API slice added on 2026-07-03: demo-tenant posted invoice/bill with TCS/TDS -> GSTR-3B -> GSTR-1/CDNR -> GSTR-2B reconciliation -> CMP-08/GSTR-4 route shape -> GST settlement preview/post/reverse -> temporary period lock/unlock -> document cleanup.~~
- ~~[x] Phase 3 Opening Balance browser shell hardening passed locally on 2026-07-03: CSV upload -> maker-checker preview -> party-wise debtor/creditor evidence -> Opening Balance Equity balancing line -> admin post -> trial balance impact -> customer statement opening balance -> existing-entry override warning -> export route evidence.~~
- ~~[x] Phase 3 Year-End Close browser shell hardening passed locally on 2026-07-03: FY selection -> close preview -> income/expense closing lines -> retained earnings movement -> admin post -> already-closed/idempotency warning -> reopen-by-reversal guidance.~~
- ~~[x] Phase 3 Inventory local API/browser hardening passed on 2026-07-04: item master tenant/app/entity scoping, item-reference validation, posted same-scope stock register assembly, closing-stock journal posting guards, route contract coverage, and mocked-shell item/register/closing-stock posting UX.~~
- ~~[x] Phase 3 Banking/Reconciliation local API/browser hardening passed on 2026-07-04: bank statement CSV import/dedupe, tenant/app/entity-scoped BRS assembly, exact amount/side match validation, soft unmatch/reversal, route contract coverage, and mocked-shell import -> match -> BRS -> unmatch UX.~~

## Closed Local Gate: Phase 3 Core Business Workflow Mutation

- ~~[x] Provision or confirm the local demo tenant `demo-mitrabooks-business`.~~
- ~~[x] Configure the MitraBooks ERP demo admin per `docs/operations/MITRABOOKS_ERP_DEMO_CREDENTIALS.md`; use `business.admin@sanmitra.local` as the operator email and keep the password only in runtime/deployment secrets.~~
- ~~[x] Reset or reseed `demo-mitrabooks-business` before local destructive browser mutation.~~
- ~~[x] Run the guarded policy check locally:~~

```powershell
$env:MITRABOOKS_DEMO_E2E_CONFIRM="demo-mitrabooks-business"
$env:E2E_USER_EMAIL="business.admin@sanmitra.local"
$env:E2E_USER_PASSWORD="<local demo password>"
python scripts/mitrabooks_phase3_business_gate.py --staging-url http://127.0.0.1:3300/mitrabooks-erp/ --destructive-demo-policy-check --demo-tenant-id demo-mitrabooks-business
```

- ~~[x] Run destructive local browser E2E only against `demo-mitrabooks-business`: party -> voucher -> sales invoice -> purchase bill -> credit note -> debit note -> report/drill-down -> reverse/cancel.~~
- ~~[x] Record pass evidence in `docs/operations/MITRABOOKS_PHASE3_BUSINESS_WORKFLOW_SIGNOFF.md`.~~
- [ ] Reseed or discard local demo data after mutation if the local database must return to a clean baseline; generated documents were reversed/cancelled by the E2E, but generated parties may remain as test data.

## Closed Hosted Gate: Phase 3 Business Workflow Mutation

- ~~[x] Confirm hosted staging backend has the MitraBooks demo admin secrets from `docs/operations/MITRABOOKS_ERP_DEMO_CREDENTIALS.md`.~~
- ~~[x] Reset or reseed hosted `demo-mitrabooks-business` before destructive browser mutation.~~
- ~~[x] Run the guarded policy check against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`.~~
- ~~[x] Run destructive hosted browser E2E only against `demo-mitrabooks-business`.~~
- [ ] Reseed or discard hosted staging demo data after mutation if the hosted demo tenant must return to a clean baseline; generated documents were reversed/cancelled by the E2E, but generated parties may remain as test data.

## Phase 3 Open Gaps

- ~~[x] Sales invoice API/E2E depth against real backend service/accounting layers for create -> approve/post -> report/statement/PDF/export -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; further visual/template signoff stays under print/PDF production review.
- ~~[x] Purchase bill API/E2E depth against real backend service/accounting layers for create -> approve/post -> report/vendor statement/export -> payment/ITC paths -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; dedicated purchase-bill PDF is not implemented yet and remains under print/export production polish.
- ~~[x] Credit note API/E2E depth against real backend service/accounting layers for source invoice linkage -> approve/post -> report/customer statement/export -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; dedicated credit-note PDF/template polish remains under print/export production review.
- ~~[x] Debit note API/E2E depth against real backend service/accounting layers for source bill linkage -> approve/post -> report/vendor statement/export -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; dedicated debit-note PDF/template polish remains under print/export production review.
- ~~[x] Receivables browser E2E for statements, ageing, allocation, reminders/dunning, and collection status UX in the mocked local MitraBooks shell.~~ Real-stack/deployed receivables mutation remains part of later demo-tenant production signoff.
- ~~[x] Payables browser E2E for vendor statements, ageing, bill payment marking, TDS, payment planning, and payout/export surfaces in the mocked local MitraBooks shell.~~ Real-stack/deployed payables mutation remains part of later demo-tenant production signoff.
- [~] GST/TDS compliance signoff for setup, rates, locks, settlement, filing semantics, and tenant GST profile UX. Local mocked-shell coverage is closed for GST profile evidence, settlement posting, GSTR-3B, GSTR-1, TDS register, and period locks. Guarded real-stack demo coverage now exercises posted TCS/TDS documents, GSTR-3B, GSTR-1/CDNR, GSTR-2B reconciliation, CMP-08/GSTR-4 route shape, GST settlement preview/post/reverse, and temporary period lock/unlock. Production compliance review remains open.
- [~] Opening balance browser E2E, maker-checker review, and rollback/reversal runbook examples. Local mocked-shell browser coverage is closed for CSV preview/post/export, party-wise opening balances, balancing line, trial balance impact, statement impact, and existing-entry warning; real-stack mutation, production operator maker-checker review, and reversal runbook examples remain open.
- [~] Year-end close browser E2E, maker-checker review, and rollback/reversal runbook examples. Local mocked-shell browser coverage is closed for FY close preview, income/expense closing lines, retained earnings movement, admin post, already-closed/idempotency warning, and reopen-by-reversal guidance; real-stack mutation, production operator maker-checker review, and reversal runbook examples remain open.
- [ ] Keyboard-first voucher/business-entry polish after route/API contracts are stable.
- [ ] Multi-client CA/bookkeeper accounting entity model and scoped client/book access rules.

## Phase 4 Open Gaps

- [~] Credit note source-document linkage and accounting/report/reversal API depth are closed; dedicated browser source-document enforcement and print/export polish remain open for production signoff.
- [~] Debit note source-document linkage and accounting/report/reversal API depth are closed; dedicated browser source-document enforcement and print/export polish remain open for production signoff.
- [~] GST report browser E2E for GSTR-1, GSTR-3B, GSTR-2B reconciliation, CMP-08, GSTR-4, settlement, and export hardening. Guarded real-stack route/report coverage exists for returns and settlement preview/post/reverse; export hardening, visual filing UX, and production compliance review remain open.
- [~] Inventory browser/API E2E for item master, stock register, closing-stock posting, valuation policy settings, stock issue, and stock adjustment. Local API and mocked-shell browser coverage is closed for item master, stock register, and closing-stock posting; valuation policy settings, stock issue/adjustment, real-stack/demo mutation, and production inventory signoff remain open.
- [~] Banking/reconciliation browser/API E2E for CSV import, matching, reversal, reconciliation summary, bank book, and cash book polish. Local API and mocked-shell browser coverage is closed for CSV import/dedupe, matching, BRS summary, and unmatch; bank-only voucher posting, bank/cash book polish, real-stack/demo mutation, and production banking signoff remain open.
- [ ] Fixed-asset disposal workflow, browser E2E, depreciation posting review, and compliance review.
- [ ] Dimensions/tagging coverage across vouchers, invoices, bills, notes, reports, and exports.
- [ ] Multi-location/branch dimension and consolidated reporting.
- [ ] Tenant-scoped document upload inbox with manual review, attachment linking, audit trail, and client/book scoping.

## Phase 5 Open Gaps

- [ ] MIS KPI contracts for monthly sales/purchase trends, top customers/vendors, working capital, overdue dashboards, and financial-health summaries.
- [ ] Data Health Score rules for missing GSTIN, unposted drafts, stale reconciliation, duplicate invoices, and overdue exposure.
- [ ] Data-health issue list with actionable remediation workflow.
- [ ] Tenant-safe Excel/PDF/JSON export governance with permissions and audit.
- [ ] Tally XML export design or proof of concept.

## Deferred Scope

- [ ] Live GST IRP/e-invoice API integration after compliance review and tenant policy are ready.
- [ ] Live e-way bill API integration after compliance review and tenant policy are ready.
- [ ] Bank API sync and bank execution after provider contracts, tenant authorization, and E2E checks are complete.
- [ ] OCR/AI document extraction and suggested account allocation after deterministic document workflow passes E2E.
- [ ] AI MIS summaries after MIS data contracts are stable and source-backed.
- [ ] Advanced batch/serial/multi-location inventory after basic inventory E2E is stable.
- [ ] SaaS backup/restore and tenant export policy.
- [ ] Mobile apps after the web ERP is stable.
- [ ] Desktop Electron, SQLite local database, hardware fingerprinting, and desktop licensing remain out of current unified ERP scope.

## MandirMitra Inside MitraBooks ERP

- [ ] MandirMitra donation create -> receipt -> accounting report -> cancel/reverse browser E2E inside the ERP shell.
- [ ] MandirMitra seva booking -> receipt -> accounting report -> cancel/reverse browser E2E inside the ERP shell.
- [ ] Hundi, festival, fund, and sponsorship accounting sub-gates after MitraBooks business core destructive staging mutation is closed.
- [ ] 80G/FCRA tenant configuration, eligibility, receipt text, and reports remain default-off until implemented and reviewed.

## GruhaMitra Inside MitraBooks ERP

- [ ] GruhaMitra maintenance bill -> collection -> accounting report -> reverse browser E2E inside the ERP shell.
- [ ] Housing unit/resident lifecycle browser E2E with tenant isolation and audit checks.
- [ ] Complaints/service requests, parking, vendors, and society accounting sub-gates after MandirMitra ERP workflows pass.

## Combined ERP Regression

- [ ] Combined MitraBooks, MandirMitra, and GruhaMitra ERP regression after each individual product workflow gate passes.
- [ ] Cross-app tenant/app-key isolation checks across business, temple, and housing workflows.
- [ ] Module visibility and permissions regression based on enabled modules, not hardcoded product names.
- [ ] Mixed workflow accounting report regression after business invoices, temple donations/sevas, and housing maintenance collections post in the same ERP environment.

## Non-Goals

- Do not mark a pending item as complete without evidence in the relevant gate/report.
- Do not run destructive staging actions on real tenant data.
- Do not treat provider configuration shells as live integrations.
- Do not include InvestMitra in SanMitra unified ERP scope.
