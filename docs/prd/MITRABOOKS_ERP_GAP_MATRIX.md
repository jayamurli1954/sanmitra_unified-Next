# MitraBooks ERP Gap Matrix

## Purpose

This document preserves the useful MitraBooks product scope from the legacy `jayamurli1954/MitraBooks` repository while keeping the current SanMitra Unified Next architecture clear.

The legacy MitraBooks documents included both cloud/SaaS plans and a later desktop-first single-user plan. The current target is not the desktop plan. The current target is a SaaS-first MitraBooks Unified ERP experience backed by the SanMitra modular monolith and shared PostgreSQL accounting engine.

## Reference Material Reviewed

Current state:

- `D:\sanmitra_unified-Next` is the active workspace.
- `D:\sanmitra-backend` is reference-only.
- Legacy MitraBooks repository documents were reviewed for product intent, not copied as architecture.

Legacy references that informed this matrix:

- `README.md`
- `PRD.md`
- `PRD_REVISED_COMPLETE.md`
- `PRD_REVISION_SUMMARY.md`
- `ENHANCED_FEATURE_PLAN.md`
- `DESKTOP_EDITION_INDEX.md`
- `DESKTOP_EDITION_SPECS.md`
- `DESKTOP_CONFIGURATION_SYSTEM.md`
- `DATA_HEALTH_SCORE_SPECIFICATION.md`
- `AI_MIS_INTEGRATION_STRATEGY.md`
- `QUALITY_ASSURANCE_STRATEGY.md`
- `TECHNICAL_REVIEW_DETAILED.md`

## Current State

The current workspace already has foundation pieces for the unified platform:

- Module registry and `enabled_modules`.
- Organization type and app-key separation.
- Shared accounting engine with tenant-scoped accounts, journals, journal lines, ledger reports, trial balance, profit and loss, receipts and payments, and balance sheet.
- Idempotent journal posting and journal reversal support.
- Staged E2E plan for LegalMitra baseline, MitraBooks ERP core, MandirMitra, GruhaMitra, and combined ERP regression.
- Lightweight target frontend shells for MitraBooks ERP and LegalMitra.

Current gap:

- MitraBooks business workflows now have implemented backend slices for parties, typed vouchers, sales invoices, purchase bills, credit/debit notes, GST preparation reports, TDS/TCS, payment allocation, statements, bank reconciliation, fixed assets, dimensions, inventory, opening balances, and year-end close.
- Phase 1 high-risk hardening is implemented locally: cross-store compensation coverage is implemented across typed vouchers, sales invoices, purchase bills, credit notes, debit notes, GST settlement, payroll, and bulk import; CA access now uses token-based invite acceptance with invite expiry, single-use acceptance, revoke handling, public acceptance UX, and browser coverage.
- Remaining gaps are deeper browser E2E coverage, compliance review, role/approval depth, advanced inventory, data health, MIS, export portability, deeper CA/bookkeeper practice modeling, and AI/document workflow depth beyond review-first shells.
- The legacy desktop plan contains useful product ideas but incompatible architecture assumptions.

## Progress Log

Update this section as implementation and E2E checks progress. Do not move a planned item into current state until code, route contracts, and the relevant smoke/tests have passed.

| Date | Area | Status | Evidence | Remaining gap |
| --- | --- | --- | --- | --- |
| 2026-05-21 | MandirMitra receipt/accounting smoke | Verified locally | Donation receipt PDF, seva receipt PDF, expense posting, trial balance, voucher drill-down, Income and Expenditure, Receipts and Payments, and Balance Sheet were checked against the local backend and MitraBooks ERP shell | Expand into repeatable Stage 3 E2E checklist and scripted browser/API smoke |
| 2026-05-21 | MandirMitra seed tenant module context | Fixed and committed | Commit `73ebf0b` preserves `seed-tenant-1` as `TEMPLE` with `temple`, `accounting`, and `audit`; `/api/v1/modules/me` returned all three enabled modules for `mandirmitra` | Apply the same discipline to all demo/bootstrap tenants before production seed strategy is finalized |
| 2026-05-21 | Execution priority | MandirMitra live-readiness first | Platform owner direction: complete MandirMitra in all aspects and make it live-ready like LegalMitra, then take GruhaMitra because both frontends are already live in the legacy platform | Keep Phase 2 business work behind the MandirMitra live-ready gate unless it directly supports MandirMitra accounting or shell stability |
| 2026-05-21 | Prior planning recap | Captured | Earlier planning sessions established the sequence: LegalMitra stable, MitraBooks accounting base, MandirMitra live-ready, GruhaMitra live-ready, then full MitraBooks business ERP expansion | Keep later business ERP operating models as product vision, not current implementation scope |
| 2026-05-21 | MandirMitra Stage 3 smoke | Added and passed | `python scripts\mandirmitra_stage3_smoke.py` passed compile checks and 119 focused tests; checklist added at `docs/operations/MANDIRMITRA_STAGE3_SMOKE_CHECKLIST.md` | Complete live browser/API checklist before deployment signoff |
| 2026-05-21 | MandirMitra public payment live smoke | Backend/API live smoke passed | Local public payment flow was verified end to end with seeded test data: public donation submission, staff verification, correction, rejection, audit trace, receipt PDF, reports, drill-down, and voucher detail | Keep real public trusts read-only in staging; use the explicit demo bootstrap tenant for destructive checks |
| 2026-05-21 | MandirMitra ERP browser smoke | Passed locally | `python scripts\mandirmitra_stage3_browser_smoke.py` verified the local MitraBooks ERP shell in MandirMitra mode and saved a screenshot under `tmp` | Complete deployment-readiness review |
| 2026-05-22 | MandirMitra Panchang workspace | Wired in ERP shell | Panchang now has a rendered MandirMitra workspace backed by `/api/v1/panchang/today`; browser smoke verifies Today Panchang and Tithi content | Continue deployment-readiness review and remaining legacy-live workflow gaps |
| 2026-05-22 | MandirMitra deployment-readiness review | Captured | `docs/operations/MANDIRMITRA_DEPLOYMENT_READINESS_REVIEW.md` records environment, seed/demo tenant, audit retention, backup/restore, rollback, hundi/fund/cancellation, 80G/FCRA, and devotee privacy gaps | Push current batch and review CI/staging before production signoff |
| 2026-05-22 | MandirMitra Reports workspace | Wired in ERP shell | Reports is now separate from Receipts and renders donation category, detailed donation, detailed seva, seva schedule, and recent devotee data | Continue live workflow review for export/print and any legacy-only report variants |
| 2026-05-22 | MandirMitra first live-cut decisions | Captured | Donation, seva, public payment, receipt, Panchang, reports, accounting, and receipt cancellation/reversal are included; Hundi/fund/festival, refund approval/settlement depth, and 80G/FCRA issuance are deferred until gates are implemented and tested | Confirm deployment environment, seed/demo policy, backup/restore, rollback, and CI/staging |
| 2026-05-22 | MandirMitra sponsorship accounting | Backend posting and basic UI covered | Cash sponsorship posts to Sponsorship Income; valued in-kind Annadanam posts to expense when inventory is off and inventory when inventory is on; precious articles classify to temple asset accounts; quick-entry captures event/item/quantity/valuation basis; focused tests pass | Add valuation approval, stock consumption, and event/fund subledger reporting in a later slice |
| 2026-05-22 | MandirMitra receipt cancellation/reversal | Backend and ERP action covered | Donation/seva receipt cancellation posts a linked reversal journal, records reason/actor/timestamp/refund metadata, returns idempotently on repeat, and keeps original receipt values unchanged | Add refund approval queue, payout settlement status, and refund export/reporting in a later slice |
| 2026-05-22 | MandirMitra CI/staging gate | CI and Render green | GitHub CI and Render workflow deployment are green; local demo receipt reversal created a `REV-*` voucher and accounting reports stayed balanced/consistent | Use only non-destructive staging checks unless a clearly marked demo/test temple tenant is available |
| 2026-05-22 | MandirMitra public payment visibility | Public page linked | ERP Public Payments workspace links to `/mandir-public/` for no-login temple selector and public payment config visibility without creating a payment | Add full devotee submission UX after demo/staging tenant policy is clear |
| 2026-05-22 | MandirMitra demo public payment submission | Passed demo smoke | `/mandir-public/` submitted a demo pending payment; ERP Public Payments showed it; staff verification posted it with dummy UTR/reference; receipt download, reports, balanced Trial Balance, and voucher drill-down passed | Keep live trust public flow visibility-only unless explicitly using a demo/test tenant |
| 2026-05-22 | MandirMitra production signoff | Checklist added | `docs/operations/MANDIRMITRA_PRODUCTION_SIGNOFF.md` records first-live included scope, deferred scope, tenant safety, accounting safety, and pending production gates | Confirm production environment, backup/restore, rollback tag/process, and tenant seed/demo policy before go-live |
| 2026-05-22 | MandirMitra final local browser smoke | Passed | `python scripts\mandirmitra_stage3_browser_smoke.py --api-base http://127.0.0.1:8001` passed with `organization_type=TEMPLE` and enabled modules `accounting`, `audit`, and `temple` | Confirm CI/Render for final signoff commit and complete production gates |
| 2026-05-22 | MandirMitra production gates | Partially confirmed | Production DB/JWT/app-key/bootstrap/PDF fallback and tenant safety policies are confirmed; production access must use real admin email with no shared default password | Finalize MitraBooks ERP production frontend URL, backup/restore setup, and release tag/rollback execution |
| 2026-05-22 | MandirMitra staging smoke | Non-destructive checks passed | Login/module context, tabs, receipt preview/download, Panchang, reports, balanced accounting reports, and public no-login UPI/config visibility passed without mutating real trust data | Enable the explicit Mandir demo bootstrap tenant with demo UPI/config before destructive staging checks |
| 2026-05-21 | Platform owner dashboard and tenant entitlements | Pending review in working tree | Backend/router/docs/tests exist locally but are not yet committed in the current reviewed batch | Review scope, run focused tests, then commit as Phase 1 foundation work if accepted |
| 2026-05-21 | Business parties and typed vouchers | Pending review in working tree | `/api/v1/business` source and tests exist locally but are not yet committed in the current reviewed batch | Treat as Phase 2; review separately from foundation/audit/platform-owner work |
| 2026-06-26 | Phase 1 accounting compensation boundary | Implemented but not production-ready | Payroll and bulk import were already covered; MitraBooks business posting flows now cover typed vouchers, sales invoices, purchase bills, credit notes, debit notes, and GST settlement with compensation reversal tests for journal-posted/Mongo-failed paths | Expand the same rigor to any remaining receipt/refund-style flows and add browser E2E over the business lifecycle |
| 2026-06-26 | Phase 1 CA access hardening | Backend implemented | Plaintext password exposure is removed; CA invites are token-based, acceptance sets the password on first use, expiry/revoke/accepted checks are enforced, and focused tests cover the backend flow | Frontend acceptance UX closed on 2026-07-01; wider CA practice modeling remains later scope |
| 2026-07-01 | Phase 1 CA acceptance UX closeout | Implemented locally | Added `/mitrabooks-erp/ca-invite-accept.html` and focused browser coverage for invite preview, password mismatch blocking, successful acceptance, missing token, and expired invite states; operator copy now refers to secure invite links instead of temporary passwords | Deploy and validate in staging as part of Phase 2E before production claims |
| 2026-06-27 | Phase 2 settings / CA practice / integrations shells | Implemented but not production-ready | Tenant-scoped business admin settings now save organization/branches/roles/permissions/controls/templates/notifications/billing plus integration and AI review-first config shells; CA Practice Portal now has tenant-scoped client master records, company switching, document queues, and document attachments with route-contract and focused test coverage | Run full local frontend preflight, extend browser E2E depth, and keep staging/provider/compliance claims conservative |

## Target State

MitraBooks Unified ERP should become the accounting-heavy operating shell for:

- MitraBooks business and professional accounting workflows.
- MandirMitra temple/trust/NGO workflows.
- GruhaMitra housing society workflows.

The MitraBooks business and professional modules should support business accounting workflows through the shared accounting engine. Domain records may live in MongoDB where they are operational records; financial postings must live in PostgreSQL through the accounting service.

## Active Scope Lock

MitraBooks has two roles, and they must not be mixed up during current execution:

1. Current role: shared accounting engine, ERP shell, tenant/app-context layer, module access layer, audit/reporting base, and route-contract foundation for MandirMitra first and GruhaMitra next.
2. Later role: full business ERP product with parties, vouchers, sales, purchases, GST, inventory, AR/AP, MIS, exports, and CA/bookkeeper workflows.

Current delivery rule:

- Complete the current role only as far as needed to make MandirMitra live-ready.
- Then complete the same base for GruhaMitra and make GruhaMitra live-ready.
- Defer the larger MitraBooks business ERP roadmap until MandirMitra and GruhaMitra are completed and deployed live.

Allowed before MandirMitra/GruhaMitra live:

- Shared journal posting, reversal, idempotency, reports, trial balance, balance sheet, income and expenditure, receipts and payments.
- Tenant/app-key/module access hardening.
- Audit events and route contracts needed by MandirMitra/GruhaMitra.
- Platform-owner controls needed to onboard, enable, and operate MandirMitra/GruhaMitra tenants.
- MandirMitra public devotee payment, staff verification, receipt preview/download, exception correction/rejection, and donation/seva accounting flows.
- MandirMitra sponsorship posting where cash support credits sponsorship income and valued in-kind support debits expense, inventory, or temple asset accounts through MitraBooks journals according to temple settings and item type.
- MandirMitra receipt cancellation/reversal for donation and seva receipts using linked reversal journals and immutable original receipt values.
- GruhaMitra accounting/reporting support only after the MandirMitra live-ready gate passes.

Deferred before MandirMitra/GruhaMitra live:

- CA/bookkeeper multi-client practice model, client upload inbox, AI bookkeeping, data health score, advanced MIS, advanced inventory, Tally XML export, bank API sync, and production filing integrations.

## Envisaged Operating Models

MitraBooks should be designed so these operating models can be introduced in phases. They are not all immediate implementation scope, but early data modeling and access-control decisions must not block them.

| Operating model | Target user | Design implication | Phase |
| --- | --- | --- | --- |
| Single user, single location | Small trader, freelancer, small professional office | One tenant, one accounting entity, one primary user, simple books | Phase 1 |
| Multi-user, single location | SME with owner, accountant, cashier, manager | RBAC, approval permissions, audit trail, role-limited posting | Phase 2 |
| Multi-user, multi-client, single location | CA firm, tax consultant, professional bookkeeper | Practice tenant manages many client books; user access must be scoped per client/accounting entity | Phase 3 |
| Multi-user, multi-location | Business with branches, warehouses, offices | Locations/branches linked to one tenant and accounting entity strategy; reports by location and consolidated | Phase 4 |
| Client-to-practice document workflow | CA/bookkeeper clients uploading bills, invoices, receipts, bank statements | Document inbox, upload permissions, client tagging, review queue, audit trail | Phase 4 |
| AI-assisted bookkeeping | CA/bookkeeper/user reviewing extracted documents | OCR/extraction, suggested account allocation, confidence score, human verification before posting | Deferred until document workflow is stable |

Key modeling rule:

- Do not treat `tenant_id` alone as the client/book boundary for CA and bookkeeper workflows. A CA or bookkeeping practice may be one tenant that manages multiple client accounting entities. Access must eventually support tenant, accounting entity/client, location, role, and permission together.

## Decision Summary

| Legacy idea | Decision | Reason |
| --- | --- | --- |
| Double-entry accounting | Preserve and strengthen | Already core to the shared accounting engine |
| Tally-style voucher speed | Preserve as UX goal | Useful for Indian accounting users even in SaaS |
| Customers, vendors, parties | Preserve | Required for real business accounting |
| Sales and purchase invoices | Preserve | Required MitraBooks ERP scope |
| GST invoice calculation and reports | Preserve, phase carefully | Critical for Indian SMEs but high-risk compliance scope |
| Inventory with FIFO | Preserve as later module | Useful, but should follow business master and invoice foundations |
| AR/AP outstanding and ageing | Preserve | Essential business reports missing from GL-only accounting |
| Data Health Score | Preserve as planned dashboard | Strong product idea for cleanup and readiness |
| MIS and AI insights | Preserve, defer AI | Deterministic reports must come before AI summaries |
| Export to Excel/PDF/JSON/Tally XML | Preserve as data portability target | Useful for trust and migration, but must be tenant-safe |
| Electron + SQLite desktop-first product | Reject for current platform | Conflicts with SaaS modular-monolith direction |
| Direct balance mutation | Reject | Conflicts with journal-only accounting doctrine |
| SQLite `REAL` or floating money | Reject | Conflicts with precision policy |
| Single-user license hardware locking | Reject for current platform | Desktop-era licensing concern, not foundation scope |
| Phone-home beta telemetry | Reject unless separately approved | Privacy and trust risk |

## Gap Matrix

| Area | Current state | Target state | Gap | Phase |
| --- | --- | --- | --- | --- |
| Accounting foundation | Journal posting, reversal, ledger, trial balance, P&L, receipts/payments, balance sheet exist | Stable accounting core for all ERP modules | Harden tests, route contracts, tenant/app-key coverage | Phase 1 |
| MandirMitra sponsorship accounting | Backend donation posting handles cash sponsorship income, valued in-kind sponsorship income, Annadanam consumables as expense when inventory is off or inventory when on, directly consumed event support, precious temple asset classification, and basic quick-entry/report metadata | Full sponsorship management by event/fund with valuation approvals, stock consumption, receipt/report polish, and drill-down reporting | Add approval workflow, event/fund subledger, and stock issue/consumption tests | Phase 1 |
| MandirMitra receipt cancellation/reversal | Donation and seva receipt cancellation actions post linked reversal journals, store reason/actor/timestamp/refund metadata, and return idempotently on repeat | Full cancellation/refund operations with approval queue, payout settlement, exports, and richer audit drill-down | Add approval workflow, settlement status, refund reports, and browser E2E | Phase 1 |
| Chart of Accounts | Default accounts and source account mapping exist | Business-type COA templates for retail, trading, services, professional, temple, housing | Add template selection and migration-safe onboarding | Phase 1 |
| MandirMitra onboarding | Module-wise temple first-login onboarding exists | Temple/trust onboarding remains module-wise, requires explicit `X-App-Key`, and creates a `TEMPLE` tenant with `temple`, `accounting`, and `audit` modules | Keep central onboarding as legacy/admin support, not the primary MandirMitra path | Phase 1 |
| Platform owner dashboard | Backend contract exists at `GET /api/v1/platform-owner/dashboard`; UI preview can call super-admin onboarding endpoints; approval derives tenant org/modules/app keys from onboarding `app_key`; payment and document verification states are tracked before approval; tenant entitlement endpoint and structured UI action can update subscription plan and enabled modules | Cross-product owner dashboard for LegalMitra, MandirMitra, GruhaMitra, and MitraBooks onboarding status, payment/document verification, approvals, subscriptions, module enablement, and KPIs | Add full browser E2E after a super-admin login path is available in the current environment | Phase 1 |
| Voucher entry | `/api/v1/business/vouchers` posts payment, receipt, contra, and journal vouchers through the accounting service with generated numbers, idempotency, listing, detail lookup, accounting-backed reversal, frontend integration, audit events, and route-contract coverage | Tally-familiar voucher speed with approval/cancel policy depth | Add browser E2E, keyboard-first entry polish, and richer audit UI | Phase 2 |
| Parties | `/api/v1/business/parties` supports tenant/app-key scoped party creation, listing, lookup, profile update, soft deactivation, frontend integration, audit events, and route-contract coverage; live balances are derived from party-ledger/outstanding reports, not Mongo party fields | Unified party/customer/vendor/client master with payment terms and ledger-derived balances | Add payment terms, credit limits, professional/client labels, and browser E2E | Phase 2 |
| Sales invoices | Implemented but not production-ready under `/api/v1/business/invoices`; invoices now create as `draft` or `pending_approval`, approve-to-post through the accounting service, compensate on domain persistence failure, support cancellation reversal, and block PDF output for non-posted documents | Production-ready sales lifecycle with approval, receipts allocation, compliance review, and print/export polish | Add browser E2E, compliance signoff, richer templates, and any remaining receipt/refund compensation depth | Phase 3 |
| Purchase invoices | Implemented but not production-ready under `/api/v1/business/bills`; bills now create as `draft` or `pending_approval`, approve-to-post through the accounting service, compensate on domain persistence failure, support payment marking/ITC reversal/reclaim/cancellation reversal, and expose approval review endpoints | Production-ready purchase lifecycle with approvals, vendor payment planning, and compliance review | Add browser E2E, attachment/document support, a posted-only output guard when a bill print/export route is added, and compliance signoff | Phase 3 |
| Credit/debit notes | Implemented but not production-ready under `/api/v1/business/credit-notes` and `/api/v1/business/debit-notes` with GL posting, compensation reversal on persistence failure, approval review endpoints, and cancellation reversal | Adjustment documents linked tightly to source invoices/bills and return workflows | Add source-document enforcement, browser E2E, and print/export polish | Phase 4 |
| GST setup | Invoice settings and GST/TDS modules support GSTIN/place-of-supply/HSN/SAC basics, GST period locks, RCM, composition, settlement, and e-invoice readiness | Tenant GST profile with reviewed jurisdiction/effective-date rules and production filing boundaries | Add compliance review, effective-date tax configuration, and stronger tenant GST profile UX | Phase 3 |
| GST reports | Implemented GSTR-1, GSTR-3B, GSTR-2B reconciliation, CMP-08, GSTR-4, GST settlement, and export/report UI slices | Production-ready preparation reports that reconcile to posted invoices and ledger with reviewed filing semantics | Add browser E2E, compliance signoff, and filing/export format hardening | Phase 4 |
| E-invoice/e-way bill | E-invoice readiness, INV-01 payload, and manual IRN recording are implemented; live IRP/e-way bill API integration is not enabled | Optional integration-ready design with tenant policy, credentials, and provider failure handling | Defer live IRP/e-way bill API integration until GST compliance review passes | Deferred |
| Inventory | Implemented opt-in inventory accounting, item master, stock register, item tags on document lines, and closing-stock journal posting with weighted-average valuation | Inventory module with configurable valuation, stock movement audit, multi-location, and advanced item controls | Add browser E2E, valuation policy settings, stock issue/adjustment workflows, and multi-location later | Phase 4 |
| Batch/serial/multi-location inventory | Legacy planned | Advanced inventory for larger businesses | Defer until basic inventory has passing E2E | Deferred |
| Receivables | Party sub-ledger, customer statements, dunning, open-item allocation, FIFO suggestions, reconciliation, and ageing are implemented | Collection workflows with approvals, reminders, and dispute tracking | Add browser E2E, communication workflow depth, and collection status UX | Phase 3 |
| Payables | Vendor statements, open-item allocation, payable ageing, bill payment marking, TDS, and payment planning primitives are implemented | Vendor payment operations with approvals, payment batches, and due-date planning | Add browser E2E, approval workflow, and payout/export depth | Phase 3 |
| Banking and reconciliation | Manual bank statement CSV import, matching, reversal, and reconciliation summary are implemented against posted ledger lines | Bank book, cash book, manual reconciliation, and import-ready statement matching | Add browser E2E, bank book/cash book polish, and defer API bank sync | Phase 4 |
| Fixed assets | Fixed-asset register, SLM/WDV depreciation preview, and depreciation journal posting are implemented | Asset lifecycle with acquisition/disposal, depreciation, and audit reporting | Add disposal workflow, browser E2E, and compliance review | Phase 4 |
| Dimensions | Cost-centre and project masters, document tags, and income/expense/net dimension reports are implemented | Reporting dimensions across vouchers, invoices, bills, notes, and exports | Expand tagging coverage where missing and add browser E2E | Phase 4 |
| Opening and year-end close | CSV opening-balance preview/posting and year-end close preview/posting are implemented through controlled journals | Migration-safe opening balances and auditable financial-year close | Add browser E2E, maker-checker workflow, and rollback/reversal runbook examples | Phase 3 |
| MIS | Ledger-backed dashboard and financial-health summary exist | KPI summary, monthly sales/purchase trend, top customers/vendors, working capital, overdue dashboards | Expand deterministic MIS contracts before AI summaries | Phase 5 |
| AI MIS | Legacy planned | Source-backed AI summaries over deterministic reports | Defer until MIS data contracts are stable | Deferred |
| Data Health Score | Legacy planned only | Data quality dashboard for missing GSTIN, unposted drafts, stale reconciliation, duplicate invoices, overdue exposure | Define scoring rules and issue list | Phase 5 |
| Data portability | Legacy emphasized exports | Tenant-safe Excel/PDF/JSON exports and planned Tally XML export | Define export permissions, audit, and scope | Phase 5 |
| Backup/restore | Desktop plan assumed local files | SaaS backup/restore and tenant export policy | Needs platform operations design | Deferred |
| Keyboard-first UX | Legacy planned | Fast entry screens with shortcuts where useful | Frontend implementation detail after API contracts | Phase 3 |
| Multi-client CA/bookkeeper practice | Envisaged but not yet modeled | Practice tenant can manage multiple client books with scoped users and approvals | Add accounting entity/client model and access rules | Phase 3 |
| Multi-location business | Envisaged but not yet modeled | Branch/location-aware operations and reports with consolidated accounting | Add location dimension after core business workflows | Phase 4 |
| Document upload and scanning | Envisaged but not yet implemented | Client/user upload inbox for bills, invoices, receipts, statements, and supporting documents | Build after party/invoice/voucher model is stable | Phase 4 |
| AI account allocation | Envisaged but not yet implemented | AI suggests voucher/account allocation from documents; user verifies before posting | Defer until deterministic document workflow passes E2E | Deferred |
| Mobile app | Legacy future scope | Not part of current first MitraBooks ERP implementation | Avoid until web ERP is stable | Deferred |

## Implementation Sequence

Current execution priority:

1. Keep LegalMitra baseline stable.
2. Complete only the MitraBooks ERP core needed to host MandirMitra safely: tenant/app context, module access, receipt/accounting reports, audit trail, and shell navigation.
3. Complete MandirMitra live-readiness before GruhaMitra migration starts.
4. Start GruhaMitra only after the MandirMitra live-ready checklist passes.
5. Defer broad MitraBooks business workflows until the MandirMitra live-ready gate is green, except for shared accounting/reporting work needed by MandirMitra.

### Phase 1: MitraBooks ERP Core

Goal: prove the accounting and access foundation is reliable.

Build or harden:

- Module access for `business`, `professional`, `accounting`, `gst`, `inventory`, and `audit`.
- COA initialization by organization type and business type.
- Journal posting, reversal, idempotency, and reports.
- Tenant/app-key/RBAC route coverage.
- Platform owner dashboard contract for onboarding status, pending approvals, subscription status, module enablement, and cross-module KPIs.

Exit gate:

- Ledger, trial balance, P&L, balance sheet, receipts/payments, and cash/bank report work for a `BUSINESS` tenant.
- Disabled modules fail closed.
- Debits always equal credits.

### Phase 2: Business Masters and Typed Vouchers

Goal: create usable MitraBooks business accounting primitives without duplicating accounting logic.

Build:

- Party master for customer, vendor, and both.
- Payment, receipt, contra, and journal voucher APIs as typed facades over accounting service.
- Opening balance import/design through controlled journal entries.

Exit gate:

- Business users can record basic non-invoice accounting safely.
- Voucher records are tenant-scoped and app-key-scoped.
- No direct balance mutation exists.

### Phase 3: Sales, Purchases, GST Basics, AR/AP

Goal: support the common SME accounting loop.

Build:

- Sales invoice draft/post/cancel.
- Purchase invoice draft/post/cancel.
- Payment/receipt allocation to invoices.
- GSTIN and place-of-supply validation basics.
- Receivables/payables outstanding and ageing.
- Multi-client accounting entity model for CA firms and professional bookkeepers, limited to access control and client/book selection.

Exit gate:

- Posted invoices create immutable GL references.
- Payments reduce outstanding balances through journal postings.
- Invoice cancellation uses reversal/adjustment strategy.
- A CA/bookkeeper practice user can access only assigned client books.

### Phase 4: GST Reports, Inventory, Reconciliation

Goal: move from accounting records to operational compliance readiness.

Build:

- GSTR-1 preparation report.
- GSTR-3B preparation report.
- Item/service master.
- Basic FIFO stock movement.
- Cash book, bank book, and manual reconciliation.
- Location/branch dimension for multi-location businesses.
- Document inbox for client/user uploads, with manual review and attachment linking.

Exit gate:

- GST reports reconcile to posted invoices and journals.
- Inventory movement does not bypass accounting where financial impact exists.
- Uploaded documents are tenant-scoped, client/book-scoped where applicable, permissioned, and auditable.

### Phase 5: MIS, Data Health, Export

Goal: add decision support and trust features after core records are reliable.

Build:

- KPI summary.
- Sales/purchase trends.
- Top customers/vendors.
- Working capital and overdue dashboards.
- Data Health Score.
- Tenant-safe Excel/PDF/JSON exports.
- Tally XML export design or proof of concept.

Exit gate:

- Reports are reproducible from source records.
- Export actions are permissioned and audited.
- Data health issues are actionable, not decorative.

## Deferred Scope

These are not part of the immediate MitraBooks ERP implementation:

- Desktop Electron product.
- SQLite local accounting database.
- Single-user desktop licensing.
- Hardware fingerprinting or beta time-bomb enforcement.
- Production e-invoice/e-way bill API integration.
- Bank API sync.
- OCR/AI data entry and auto-allocation.
- AI MIS assistant.
- Mobile apps.
- Advanced inventory with batch, serial, manufacturing, or multi-location complexity.
- Production data migration from Tally.

## Non-Negotiable Guardrails

- PostgreSQL remains the source of truth for financial postings.
- No financial workflow may mutate balances directly.
- All posted financial documents must link to journal entries or explicit reversal/adjustment entries.
- Amounts must use fixed precision or integer minor units, never binary floating point.
- Every protected route must resolve trusted tenant, app key, organization type, enabled modules, role, and permissions.
- Every MongoDB domain query must be tenant-scoped.
- Every PostgreSQL accounting row must be tenant-scoped.
- For CA/bookkeeper workflows, every client/book operation must also be scoped to the assigned accounting entity or client record.
- AI or OCR output must never post directly. It can only create suggestions or drafts that a permitted user verifies before posting.
- GST and tax outputs must be framed as preparation/reporting until compliance review confirms production filing readiness.

## Open Questions

- Which business types should be supported first: retail/trading, services, professional, or all three?
- Should `professional` use the same party/invoice engine as `business` with different labels, or have a separate billing facade?
- What export formats are required for the first MitraBooks ERP release: PDF only, Excel also, or JSON tenant export?
- Should Tally XML import/export be a product differentiator in the first release or a later migration tool?
- What is the minimum GST scope needed before calling MitraBooks ERP usable for Indian SMEs?
- Should CA/bookkeeper clients be represented as accounting entities under one practice tenant, separate child tenants, or both depending on engagement type?
- What minimum document types should the first upload inbox accept: purchase bills, sales invoices, expense receipts, bank statements, or all supporting documents?
