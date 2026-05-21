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
- Staged E2E plan for LegalMitra baseline, MitraBooks ERP core, MandirMitra, GruhaMitra, combined ERP regression, and InvestMitra.
- Lightweight target frontend shells for MitraBooks ERP, LegalMitra, and InvestMitra.

Current gap:

- MitraBooks business workflows are not yet detailed enough for implementation.
- GST, inventory, sales, purchases, receivables, payables, MIS, data health, and export scope are named but not fully broken into buildable phases.
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
| 2026-05-21 | MandirMitra public payment live smoke | Backend/API live smoke passed | Local seed temple was configured as Parlathya Prathishtana with public UPI; public donation submission, staff verification, correction, rejection, audit trace, receipt PDF, reports, drill-down, and voucher detail were verified | Complete visual ERP browser pass and deployment-readiness review |
| 2026-05-21 | MandirMitra ERP browser smoke | Passed locally | `python scripts\mandirmitra_stage3_browser_smoke.py` verified the local MitraBooks ERP shell in MandirMitra mode and saved a screenshot under `tmp` | Complete deployment-readiness review |
| 2026-05-22 | MandirMitra Panchang workspace | Wired in ERP shell | Panchang now has a rendered MandirMitra workspace backed by `/api/v1/panchang/today`; browser smoke verifies Today Panchang and Tithi content | Continue deployment-readiness review and remaining legacy-live workflow gaps |
| 2026-05-22 | MandirMitra deployment-readiness review | Captured | `docs/operations/MANDIRMITRA_DEPLOYMENT_READINESS_REVIEW.md` records environment, seed/demo tenant, audit retention, backup/restore, rollback, hundi/fund/cancellation, 80G/FCRA, and devotee privacy gaps | Push current batch and review CI/staging before production signoff |
| 2026-05-21 | Platform owner dashboard and tenant entitlements | Pending review in working tree | Backend/router/docs/tests exist locally but are not yet committed in the current reviewed batch | Review scope, run focused tests, then commit as Phase 1 foundation work if accepted |
| 2026-05-21 | Business parties and typed vouchers | Pending review in working tree | `/api/v1/business` source and tests exist locally but are not yet committed in the current reviewed batch | Treat as Phase 2; review separately from foundation/audit/platform-owner work |

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
- GruhaMitra accounting/reporting support only after the MandirMitra live-ready gate passes.

Deferred before MandirMitra/GruhaMitra live:

- Business party master UI and deep workflow expansion.
- Sales/purchase invoice implementation.
- GST return preparation.
- Inventory and stock valuation.
- AR/AP ageing.
- MIS, data health score, exports, CA/bookkeeper practice model, document inbox, and AI bookkeeping.

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
| Chart of Accounts | Default accounts and source account mapping exist | Business-type COA templates for retail, trading, services, professional, temple, housing | Add template selection and migration-safe onboarding | Phase 1 |
| MandirMitra onboarding | Module-wise temple first-login onboarding exists | Temple/trust onboarding remains module-wise, requires explicit `X-App-Key`, and creates a `TEMPLE` tenant with `temple`, `accounting`, and `audit` modules | Keep central onboarding as legacy/admin support, not the primary MandirMitra path | Phase 1 |
| Platform owner dashboard | Backend contract exists at `GET /api/v1/platform-owner/dashboard`; UI preview can call existing super-admin approve/reject onboarding endpoints; approval derives tenant org/modules/app keys from onboarding `app_key`; tenant entitlement endpoint and structured UI action can update subscription plan and enabled modules | Cross-module owner dashboard for MandirMitra, GruhaMitra, and MitraBooks onboarding status, approvals, subscriptions, module enablement, and KPIs | Add full browser E2E after a super-admin login path is available in the current environment | Phase 1 |
| Voucher entry | Generic journal posting exists; initial `/api/v1/business/vouchers` facade posts payment, receipt, contra, and journal vouchers through the accounting service with generated voucher numbers, idempotency-key reuse, listing, detail lookup, accounting-backed reversal, backend route-contract coverage, lifecycle audit events, and tenant/app-scoped audit event query support | Tally-familiar payment, receipt, contra, journal, sales, purchase voucher flows | Add frontend integration, cancel/update policy, reversal UX, frontend manifest coverage, audit UI expansion, and browser E2E | Phase 2 |
| Parties | Initial target API slice exists under `/api/v1/business/parties` for tenant/app-key scoped party creation, listing, lookup, profile update, soft deactivation, backend route-contract coverage, lifecycle audit events, and tenant/app-scoped audit event query support; profile updates do not mutate balances | Unified party/customer/vendor/client master with GSTIN, payment terms, opening balance | Add frontend integration, frontend manifest coverage, audit UI expansion, and professional/client labels | Phase 2 |
| Sales invoices | Planned only | Draft, post, cancel, receipt-linked sales invoice with GST calculation | Implement invoice domain record plus GL posting rules | Phase 3 |
| Purchase invoices | Planned only | Draft, post, cancel, payment-linked purchase invoice with GST/ITC fields | Implement purchase workflow and payable posting | Phase 3 |
| Credit/debit notes | Legacy planned | Adjustment documents linked to invoices and GL reversals/adjustments | Add after invoice posting is stable | Phase 4 |
| GST setup | Registry has `gst`; docs mention readiness | Tenant GST profile, state/place-of-supply logic, GSTIN validation, HSN/SAC basics | Define compliance boundaries and validation rules | Phase 3 |
| GST reports | Planned | GSTR-1 and GSTR-3B preparation reports, export readiness | Build report layer after invoice data is reliable | Phase 4 |
| E-invoice/e-way bill | Legacy planned | Optional integration-ready design | Defer until GST reports and compliance review pass | Deferred |
| Inventory | Registry has `inventory`; no detailed workflow | Item/service master, units, HSN/SAC, FIFO stock movement, stock valuation | Build after invoices and posting rules are stable | Phase 4 |
| Batch/serial/multi-location inventory | Legacy planned | Advanced inventory for larger businesses | Defer until basic inventory has passing E2E | Deferred |
| Receivables | GL reports exist | Customer outstanding, ageing buckets, collection status | Needs invoice/payment linkage | Phase 3 |
| Payables | GL reports exist | Vendor outstanding, ageing buckets, payment planning | Needs purchase/payment linkage | Phase 3 |
| Banking and reconciliation | Basic cash/bank report support exists | Bank book, cash book, manual reconciliation, import-ready statement matching | Start manual; defer API bank sync | Phase 4 |
| MIS | GL reports exist | KPI summary, monthly sales/purchase trend, top customers/vendors, working capital, overdue dashboards | Build deterministic report services first | Phase 5 |
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
