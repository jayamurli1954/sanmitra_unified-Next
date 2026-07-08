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
- ~~[x] Phase 3 Opening Balance guarded real-stack demo mutation coverage added on 2026-07-07: CSV preview -> admin post with duplicate override -> export evidence -> generic journal reversal cleanup through the accounting reversal API.~~
- ~~[x] Phase 3 Year-End Close browser shell hardening passed locally on 2026-07-03: FY selection -> close preview -> income/expense closing lines -> retained earnings movement -> admin post -> already-closed/idempotency warning -> reopen-by-reversal guidance.~~
- ~~[x] Phase 3 Year-End Close guarded real-stack demo mutation coverage added on 2026-07-07: dynamic FY activity seed -> close preview -> retained earnings movement -> admin close -> already-closed guard -> generic journal reversal cleanup plus seed-voucher reversal.~~
- ~~[x] Phase 3 Inventory local API/browser hardening passed on 2026-07-04: item master tenant/app/entity scoping, item-reference validation, posted same-scope stock register assembly, closing-stock journal posting guards, route contract coverage, and mocked-shell item/register/closing-stock posting UX.~~
- ~~[x] Phase 3 Banking/Reconciliation local API/browser hardening passed on 2026-07-04: bank statement CSV import/dedupe, tenant/app/entity-scoped BRS assembly, exact amount/side match validation, soft unmatch/reversal, route contract coverage, and mocked-shell import -> match -> BRS -> unmatch UX.~~
- ~~[x] Phase 3 Fixed Assets local API/browser hardening passed on 2026-07-04: depreciation math/posting review, balanced disposal journal plan, tenant/app/entity-scoped disposal route contract, admin-only shell disposal UX, and mocked-shell register -> depreciation -> disposal workflow.~~
- ~~[x] Phase 3 Voucher Dimensions local API/browser hardening passed on 2026-07-04: typed voucher cost-centre/project tags, tenant/app/entity-scoped dimension report/export route, voucher P&L inclusion only for income/expense accounts, and mocked-shell voucher tag plus dimension export UX.~~
- ~~[x] Phase 3 Per-line Dimensions local hardening passed on 2026-07-05: sales invoice and purchase bill line-level cost-centre/project tags, dimension validation, header fallback reporting, and mocked-shell line override evidence.~~
- ~~[x] Phase 3 Branch Consolidated Reporting local hardening passed on 2026-07-05: branch settings mapped to cost-centre codes, tenant/app/entity-scoped branch P&L route, unassigned/unmapped reconciliation bucket, route-contract coverage, and mocked-shell branch rollup evidence.~~
- ~~[x] Phase 3 Credit/debit note line dimensions local hardening passed on 2026-07-05: credit note and debit note line-level cost-centre/project tags, dimension validation, header fallback reporting, and mocked-shell note line selector evidence.~~
- ~~[x] Phase 3 Tenant-scoped document upload inbox local hardening passed on 2026-07-05: CA document metadata links to tenant/app/book-scoped client records, attachments update review-queue evidence, manual review timestamps are audited, and mocked-shell coverage exercises client book selection, file upload, and review advancement.~~
- ~~[x] Phase 3 Keyboard-first voucher entry local hardening passed on 2026-07-06: voucher dialog focus, Ctrl+Alt+V open shortcut, Alt+L journal line shortcut, Ctrl+Enter balanced submit, static shortcut contract checks, and mocked-shell keyboard flow evidence.~~
- ~~[x] Phase 3 Keyboard-first business document entry parity local hardening passed on 2026-07-06: sales invoice, purchase bill, credit note, and debit note create forms expose open/focus, add-line, remove-line, and Ctrl+Enter submit keyboard evidence in the mocked shell.~~
- ~~[x] Phase 3 Inventory stock movement local hardening passed on 2026-07-07: valuation policy is explicit as weighted-average periodic, tenant/app/entity-scoped stock issue and adjustment records feed the stock register, route-contract coverage is updated, and mocked-shell evidence records a stock adjustment.~~
- ~~[x] Phase 3 Inventory guarded real-stack demo mutation coverage added on 2026-07-07: run-specific accounting entity -> inventory settings enablement -> policy check -> item master create -> stock adjustment/issue -> stock register valuation -> closing-stock journal -> generic journal reversal cleanup -> item deactivation.~~

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
- ~~[x] Reconfirmed local destructive real-stack mutation on 2026-07-07 after GST settlement persistence hardening: backend workflow pytest, frontend contract pytest, local shell smoke, local read-only shell smoke, demo policy, auth precheck, and destructive browser/API mutation all passed.~~
- [ ] Reseed or discard local demo data after mutation if the local database must return to a clean baseline; generated documents were reversed/cancelled by the E2E, but generated parties may remain as test data.

## Hosted Gate Evidence: Phase 3 Business Workflow Mutation

- ~~[x] Confirm hosted staging backend has the MitraBooks demo admin secrets from `docs/operations/MITRABOOKS_ERP_DEMO_CREDENTIALS.md`.~~
- ~~[x] Reset or reseed hosted `demo-mitrabooks-business` before destructive browser mutation.~~
- ~~[x] Run the guarded policy check against `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`.~~
- ~~[x] Run destructive hosted browser E2E only against `demo-mitrabooks-business`.~~
- [ ] Reconfirm hosted staging destructive mutation after the 2026-07-07 credential drift: latest rerun reached deployed login and failed with `Invalid credentials`, so the demo admin password/seed must be realigned before production signoff can be treated as current.
- [ ] Reseed or discard hosted staging demo data after mutation if the hosted demo tenant must return to a clean baseline; generated documents were reversed/cancelled by the E2E, but generated parties may remain as test data.

## Security P0/P1/P2 (Code Review 2026-07-05)

Living security tracker derived from:

- [`docs/operations/Code_Review-Sanmitra_Unified-Next.docx`](Code_Review-Sanmitra_Unified-Next.docx)
- [`docs/reviews/MITRABOOKS_REVIEW_2026-06-26.md`](../reviews/MITRABOOKS_REVIEW_2026-06-26.md)
- [`docs/reviews/SECURITY_REMEDIATION_PR_PLAN.md`](../reviews/SECURITY_REMEDIATION_PR_PLAN.md)

Remediation PR mapping: [`docs/reviews/SECURITY_REMEDIATION_PR_PLAN.md`](../reviews/SECURITY_REMEDIATION_PR_PLAN.md) (`PR1`–`PR13`). Full static review snapshot: [`docs/operations/Code_Review-Sanmitra_Unified-Next.docx`](Code_Review-Sanmitra_Unified-Next.docx). Mark items `~~[x]~~` only with test/PR evidence. Do not treat MitraBooks module completion as security signoff.

### Security release gate (production-hardened)

- [ ] All `[ ]` and unresolved `[~]` **P0** items below are closed.
- [ ] Hosted staging destructive mutation reconfirmed after demo credential realignment (see Hosted Gate Evidence above).
- [ ] `MANDIR_ONBOARDING_SECRET`, `JWT_SECRET`, and `OTP_PEPPER` set in production; all `*_BOOTSTRAP=false`.
- [ ] `AUTH_EMAIL_DEBUG_RETURN_LINK=false` and `MOBILE_OTP_DEBUG_RETURN_CODE=false` in production.
- [ ] `python scripts/preflight.py --all` passed on the release candidate.

### P0 — before production signoff

| ID | Item | PR | Status |
| --- | --- | --- | --- |
| SEC-P0-00 | `[CRITICAL-ACCOUNTING]` Cross-store posting boundary: PostgreSQL ledger commit before Mongo source write can orphan posted journals (`post_journal_entry`, payroll, bulk import, and similar Mongo+ledger flows). Compensation must be explicit per flow with failure tests. | — | [~] Payroll/bulk-import failure-boundary coverage added in `tests/test_hr_payroll_run.py` and `tests/test_bulk_import.py` (posting failure leaves Mongo untouched; Mongo write failure triggers reversal). Gruha maintenance now compensates bill-update-after-post failures with automatic reversal in `app/modules/housing/service.py`, covered by `tests/test_gruhamitra_security_isolation.py`. Additional `post_journal_entry` callers outside this track still require explicit flow-by-flow signoff. |
| SEC-P0-01 | `[CRITICAL-SECURITY]` Strip `hashed_password` and other internal fields from `GET /api/v1/users/me`. | PR1 | ~~[x]~~ `app/core/users/router.py` allow-list serializer; `tests/test_users_me_context.py::test_me_excludes_hashed_password` |
| SEC-P0-02 | `[CRITICAL-SECURITY]` Harden `POST /auth/register`, `/register-request`, and legacy register: no client-controlled `role`/`tenant_id` without invite/onboarding approval. | PR2 | ~~[x]~~ `app/core/auth/registration_policy.py` + hardened register paths; `tests/test_auth_registration_policy.py` |
| SEC-P0-03 | `[CRITICAL-TENANCY]` Mobile OTP and Google first-login must not assign caller-supplied `tenant_id` without invite/join-request policy. | PR3 | ~~[x]~~ OTP/Google use `resolve_self_service_tenant_id`; `tests/test_auth_google.py`, `tests/test_auth_registration_policy.py` |
| SEC-P0-04 | `[CRITICAL-TENANCY]` Mandir public payment status must scope by `tenant_id`, remove prefix-regex enumeration, and return minimal fields. | PR5 | ~~[x]~~ `mandir_public_payment_status` requires `temple_id` + exact `id` match; `tests/test_mandir_posting_guardrails.py` |
| SEC-P0-05 | `[CRITICAL-SECURITY]` Require `MANDIR_ONBOARDING_SECRET` in production startup; reject onboard without `X-Onboarding-Token` when secret is configured. | PR6 | ~~[x]~~ `Settings.validate()` prod gate + endpoint 503 fallback; `tests/test_auth_registration_policy.py` |
| SEC-P0-06 | Authenticate and rate-limit `/legal/news`, `/judgements`, `/web-search-rag` (Tavily proxy abuse). | PR7 | ~~[x]~~ `app/modules/legal/router.py` now enforces `get_current_user` + `require_enabled_module("legal")` and SlowAPI limits; `tests/test_legal_auth.py` unauth deny coverage + `tests/test_rate_limit_wiring.py` limiter wiring assertions. |
| SEC-P0-07 | Rate-limit auth endpoints: login, register, forgot/reset password, OTP send/verify. | PR4 | ~~[x]~~ SlowAPI limits added for `/auth/*` and legacy `/api/auth/*` auth routes in `app/core/auth/router.py` and `app/api/legacy_alias_router.py`; verified by `tests/test_rate_limit_wiring.py`. |

### P1 — high value, near-term

| ID | Item | PR | Status |
| --- | --- | --- | --- |
| SEC-P1-01 | Add `require_enabled_module()` + RBAC to `mandir_compat` write/financial/admin routes. | PR8 | [ ] |
| SEC-P1-02 | Add `require_enabled_module()` + RBAC to `housing_compat` write/financial/admin routes. | PR9 | [ ] |
| SEC-P1-03 | Add `require_enabled_module()` + RBAC to `mitrabooks_compat` posting/import routes. | PR10 | [ ] |
| SEC-P1-04 | Cap `housing_compat` journal attachment upload size; align with business/legal upload limits. | PR11 | [ ] |
| SEC-P1-05 | Reject invalid `X-App-Key` values instead of coercing to default app (`resolve_app_key`). | — | [ ] |
| SEC-P1-06 | Mandir public devotee autofill: minimize PII returned and tighten abuse controls. | PR5 | ~~[x]~~ Email/address removed from public autofill response; `tests/test_mandir_posting_guardrails.py::test_public_devotee_autofill_returns_minimal_pii` |
| SEC-P1-07 | Strengthen password policy (length/complexity) on register, activate, reset, and change-password. | PR11 | [ ] |
| SEC-P1-08 | Remove or env-gate `scripts/fix_superadmin.py`; replace `.env.example` literal demo passwords with placeholders. | PR13 | ~~[x]~~ `scripts/fix_superadmin.py` requires `SUPER_ADMIN_PASSWORD`; `.env.example` placeholders |
| SEC-P1-09 | Add audit events for super-admin `X-Tenant-ID` / `X-App-Key` override usage. | — | [ ] |
| SEC-P1-10 | Disable OpenAPI UI (`/docs`, `/redoc`) in production. | PR11 | [ ] |
| SEC-P1-11 | CA invite preview/accept endpoints: add rate limits; keep response free of secrets. | — | [~] Token-based invite/password-on-accept is implemented; preview rate limits and response minimization remain open. |

### P2 — hardening and maintainability

- [ ] Frontend: move access tokens off `localStorage` or tighten CSP; systematic `innerHTML` audit (`PR12`).
- [ ] Split compat router monoliths; add RBAC deny-matrix tests across roles × routes.
- [ ] Add cross-tenant RAG citation isolation tests and auth-abuse regression tests.
- [ ] Frontend monolith extraction per Code Review DOCX (`E0`–`E26`); track separately from security P0/P1.

### Security test gaps to close with P0/P1

- [ ] `register` rejects client `role=super_admin` / arbitrary `tenant_id`.
- [ ] `/users/me` never returns `hashed_password`.
- [ ] Public Mandir payment status is isolated by `tenant_id`.
- [ ] Invalid `X-App-Key` returns 401/403 (not default-app coercion).
- [ ] Mongo failure after ledger commit triggers documented compensation/reversal per flow.
- [ ] Auth endpoints return `429` under abuse thresholds.

## Phase 3 Open Gaps

- ~~[x] Sales invoice API/E2E depth against real backend service/accounting layers for create -> approve/post -> report/statement/PDF/export -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; further visual/template signoff stays under print/PDF production review.
- ~~[x] Purchase bill API/E2E depth against real backend service/accounting layers for create -> approve/post -> report/vendor statement/export -> payment/ITC paths -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; dedicated purchase-bill PDF is not implemented yet and remains under print/export production polish.
- ~~[x] Credit note API/E2E depth against real backend service/accounting layers for source invoice linkage -> approve/post -> report/customer statement/export -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; dedicated credit-note PDF/template polish remains under print/export production review.
- ~~[x] Debit note API/E2E depth against real backend service/accounting layers for source bill linkage -> approve/post -> report/vendor statement/export -> cancel/reverse.~~ Browser depth remains covered by the guarded real-stack demo mutation gate; dedicated debit-note PDF/template polish remains under print/export production review.
- ~~[x] Receivables browser E2E for statements, ageing, allocation, reminders/dunning, and collection status UX in the mocked local MitraBooks shell.~~ Real-stack/deployed receivables mutation remains part of later demo-tenant production signoff.
- ~~[x] Payables browser E2E for vendor statements, ageing, bill payment marking, TDS, payment planning, and payout/export surfaces in the mocked local MitraBooks shell.~~ Real-stack/deployed payables mutation remains part of later demo-tenant production signoff.
- [~] GST/TDS compliance signoff for setup, rates, locks, settlement, filing semantics, and tenant GST profile UX. Local mocked-shell coverage is closed for GST profile evidence, settlement posting, GSTR-3B, GSTR-1, TDS register, and period locks. Guarded real-stack demo coverage now exercises posted TCS/TDS documents, GSTR-3B, GSTR-1/CDNR, GSTR-2B reconciliation, CMP-08/GSTR-4 route shape, GST settlement preview/post/reverse, and temporary period lock/unlock. Production compliance review remains open.
- [~] Opening balance production operator maker-checker review. Local mocked-shell browser coverage is closed for CSV preview/post/export, party-wise opening balances, balancing line, trial balance impact, statement impact, and existing-entry warning; guarded real-stack demo mutation now covers preview/post/export plus reversal cleanup. Hosted production operator signoff remains open.
- [~] Year-end close production operator maker-checker review. Local mocked-shell browser coverage is closed for FY close preview, income/expense closing lines, retained earnings movement, admin post, already-closed/idempotency warning, and reopen-by-reversal guidance; guarded real-stack demo mutation now covers dynamic FY seed activity, preview, close, already-closed guard, and reversal cleanup. Hosted production operator signoff remains open.
- [~] Keyboard-first voucher/business-entry polish after route/API contracts are stable. Local voucher-entry and business document-entry keyboard coverage is closed for focus, open, add-line, remove-line, and submit shortcuts across vouchers, sales invoices, purchase bills, credit notes, and debit notes; production operator UX signoff remains open.
- ~~[x] Phase 3 Credit/Debit Note browser source-document and print/export local hardening passed on 2026-07-06: local shell enforces source invoice/bill selection, sends source ids plus numbers, and exposes printable detail plus JSON export actions.~~
- ~~[x] MitraBooks forgot/reset password and installable PWA local hardening passed on 2026-07-08: the login shell exposes forgot-password request and reset-link completion, MitraBooks reset emails route to `/mitrabooks-erp/index.html`, and Android/iPhone/iPad install prompts are covered in the shared PWA shell.~~
- [ ] Multi-client CA/bookkeeper accounting entity model and scoped client/book access rules.

## Phase 4 Open Gaps

- [~] Credit note source-document linkage and accounting/report/reversal API depth are closed; local browser source-document selection/enforcement plus JSON/print detail actions are closed; production template/export signoff remains open.
- [~] Debit note source-document linkage and accounting/report/reversal API depth are closed; local browser source-document selection/enforcement plus JSON/print detail actions are closed; production template/export signoff remains open.
- [~] GST report browser E2E for GSTR-1, GSTR-3B, GSTR-2B reconciliation, CMP-08, GSTR-4, settlement, and export hardening. Guarded real-stack route/report coverage exists for returns and settlement preview/post/reverse; export hardening, visual filing UX, and production compliance review remain open.
- [~] Inventory browser/API E2E for item master, stock register, closing-stock posting, valuation policy settings, stock issue, and stock adjustment. Local API and mocked-shell browser coverage is closed for item master, stock register, closing-stock posting, explicit weighted-average periodic valuation policy, and stock issue/adjustment records; guarded real-stack demo mutation now covers run-specific entity setup, item/movement/register/closing-stock posting, reversal cleanup, and item deactivation. Multi-location controls and production inventory signoff remain open.
- [~] Banking/reconciliation browser/API E2E for CSV import, matching, reversal, reconciliation summary, bank book, and cash book polish. Local API and mocked-shell browser coverage is closed for CSV import/dedupe, matching, BRS summary, unmatch, bank-only voucher posting from imported statement lines, and bank/cash book period reporting; guarded real-stack demo mutation now covers bank ledger voucher posting, statement CSV upload, BRS suggestion, explicit match, soft unmatch/reversal, bank-only charge classification, bank-charge voucher posting, and voucher reversal cleanup. Live bank feed policy is documented in `docs/operations/MITRABOOKS_BANK_FEED_POLICY.md`; production banking signoff remains open.
- [~] Fixed-asset disposal workflow, browser E2E, depreciation posting review, and compliance review. Local API and mocked-shell browser coverage is closed for register, depreciation preview/posting, and disposal journal UX; guarded real-stack/demo mutation now covers run-specific entity setup, fixed-asset register creation, depreciation preview/posting, balanced depreciation journal evidence, disposal journal posting, disposed-register evidence, and cross-entity denial. Dedicated gain/loss COA polish, production asset audit reporting, and compliance signoff remain open.
- [~] Dimensions/tagging coverage across vouchers, invoices, bills, notes, reports, and exports. Document-level tags and reports are covered for invoices, bills, credit notes, debit notes, and typed vouchers with local API and mocked-shell browser coverage; dimension CSV/XLSX/PDF export route hardening is locally covered. Sales invoice, purchase bill, credit note, and debit note per-line dimensions are locally covered with header fallback reporting; real-stack/demo mutation and production signoff remain open.
- [~] Multi-location/branch dimension and consolidated reporting. Local branch-to-cost-centre consolidated P&L is covered with an unassigned/unmapped reconciliation bucket and mocked-shell evidence; real-stack/demo mutation, branch selector UX across document entry, export route, and production multi-branch signoff remain open.
- [~] Tenant-scoped document upload inbox with manual review, attachment linking, audit trail, and client/book scoping. Local backend and mocked-shell coverage is closed for CA document metadata, client/book linkage, attachment upload evidence, manual review timestamps, and audit events. Object-storage/OCR provider policy is documented in `docs/operations/MITRABOOKS_DOCUMENT_UPLOAD_OCR_POLICY.md`; guarded real-stack/demo mutation coverage now exercises CA client/document creation, attachment upload/list/download, cross-book denial, manual review advancement, audit evidence, and OCR/auto-post disabled controls. Provider configuration, malware/file-type hardening, and production signoff remain open.

## Phase 5 Open Gaps

- [~] MIS KPI contracts for monthly sales/purchase trends, top customers/vendors, working capital, overdue dashboards, and financial-health summaries. Local deterministic backend contract and mocked-shell rendering are closed; real-stack/demo mutation, production report signoff, and AI MIS narration remain open.
- [~] Data Health Score rules for missing GSTIN, unposted drafts, stale reconciliation, duplicate invoices, and overdue exposure. Local deterministic backend contract, issue-list contract, mocked-shell score rendering, and remediation workspace routing are closed; real-stack/demo validation and production signoff remain open.
- [~] Data-health issue list with actionable remediation workflow. Local API issue normalization and mocked-shell remediation navigation are closed; persisted assignee/status workflow, real-stack/demo mutation, and production signoff remain open.
- [~] Tenant-safe Excel/PDF/JSON export governance with permissions and audit. Local report/dimension/opening-balance/invoice-PDF exports now use shared role checks, audit events, governed headers, and JSON report format coverage; real-stack/demo validation, wider GST JSON export governance, and production retention/signoff remain open.
- [~] Tally XML export design or proof of concept. Local governed Trial Balance ledger-master XML proof is closed with backend route, audit/governance headers, static shell button, and mocked-shell route coverage; voucher-level XML, real Tally import validation, migration runbook, and production signoff remain open.

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
