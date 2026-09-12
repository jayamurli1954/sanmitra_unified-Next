# SanMitra Unified Platform PRD

## Purpose

Create a clear foundation for merging the accounting-heavy product experiences into one maintainable ERP platform while preserving SanMitra's product brands.

## Product Brands

- GruhaMitra: housing societies, apartments, RWAs, gated communities.
- MandirMitra: temples, trusts, NGOs, donation and seva workflows.
- MitraBooks: businesses, SMEs, professionals, retailers, accounting users.
- LegalMitra: legal research, legal workflow, compliance.

InvestMitra is no longer part of the SanMitra unified backend or deployment scope. It may be developed separately for personal use only and must not be included in unified backend, Vercel, Render, tenant/module registry, billing, or E2E release planning.

## Current State

The active platform is `D:\sanmitra_unified-Next`. `D:\sanmitra-backend` is reference-only.

What exists now:

- One FastAPI modular monolith with `organization_type`, `enabled_modules`, module registry, RBAC, and `X-App-Key` product context.
- Shared PostgreSQL accounting engine with journal posting, reversal, idempotency, ledger, trial balance, P&L, balance sheet, receipts and payments, and report drill-down.
- MongoDB for tenants, users, and domain records.
- MitraBooks ERP shell hosting business, MandirMitra, and GruhaMitra workspaces.
- MitraBooks business APIs under `/api/v1/business` for parties, typed vouchers, sales invoices, purchase bills, credit/debit notes, cash AR/AP allocation, GST/TDS preparation, inventory, bank reconciliation, fixed assets, dimensions, opening balances, year-end close, MIS, data health, exports, and CA practice client books. These slices are **live in this repo and on the unified domains**. Remaining items are signoff and unfinished workflows (see Remaining Gaps in README), not a claim that the product is undeployed.
- MandirMitra donation, seva, public payment, receipt, hundi/fund, and 80G-readiness flows posting through the shared accounting engine. Production/demo-tenant mutation signoff remains open.
- GruhaMitra maintenance bill → collection → reverse hosted billing gate passed 2026-07-17. Unit/resident lifecycle and remaining society workflows remain open.

Current limitation: local and demo-tenant gates are ahead of production signoff. Do not treat preparation GST reports, integration config shells, or local E2E as production filing, live bank, or live Mandir/Gruha cutover.

## Living Progress Rules

This PRD is a living product contract for the unified platform. Update it together with `MITRABOOKS_ERP_GAP_MATRIX.md` whenever implementation changes the reliable current state, target scope, known gaps, or deferred scope.

Rules:

- Keep current state separate from target state.
- Mark uncommitted or unreviewed local work as pending review, not implemented.
- Record validation evidence when a workflow is considered verified.
- Do not promote planned integrations or future module work into current state without passing tests or smoke checks.

## Latest Progress

| Date | Area | Status | Evidence | Remaining gap |
| --- | --- | --- | --- | --- |
| 2026-09-10 | README / PRD alignment to gap matrix | Docs catch-up | README current state, remaining gaps, and this PRD MitraBooks Business Module now match `MITRABOOKS_ERP_GAP_MATRIX.md` and `MITRABOOKS_PENDING_GAP_TODO.md`: Phases 2–5 slices exist locally; production signoff is still open | Hosted destructive mutation reconfirm; Mandir demo-tenant mutation; GST/TDS compliance review; Gruha lifecycle; optional Phase 4 AR/AP netting |
| 2026-07-18 | Combined ERP read-only regression | Passed on hosted staging demo tenants | `scripts/mitrabooks_stage5_combined_regression_gate.py` across `demo-mitrabooks-business`, `demo-mandir-tenant`, and `gruhamitra-demo-society` | Optional combined destructive mutation; production claims still blocked |
| 2026-07-18 | Phase 5 MIS / data health / export read gate | Passed | `scripts/mitrabooks_phase5_mis_datahealth_export_gate.py` | Production report signoff; AI MIS remains deferred |
| 2026-07-17 | GruhaMitra billing-to-accounting | Hosted gate passed | `scripts/gruhamitra_stage4_billing_gate.py` generate → post → collection → reverse | Unit/resident lifecycle and remaining society workflows |
| 2026-07-13 | MandirMitra fund / in-kind / refund local hardening | Implemented locally | Fund subledger, maker-checker transfers, in-kind valuation, full-refund queue | Guarded two-user demo-tenant mutation and production signoff |
| --- | --- | --- | --- | --- |
| 2026-05-21 | MandirMitra in MitraBooks ERP | Receipt and accounting smoke verified locally | Donation receipt PDF, seva receipt PDF, expense posting, trial balance, voucher drill-down, Income and Expenditure, Receipts and Payments, and Balance Sheet were checked on the local backend and ERP shell | Convert this manual smoke into a repeatable Stage 3 checklist/script |
| 2026-05-21 | Tenant/module context | Seed tenant context fixed and committed | Commit `73ebf0b` keeps `seed-tenant-1` as `TEMPLE` and `/api/v1/modules/me` returns `temple`, `accounting`, and `audit` for `mandirmitra` | Review remaining bootstrap/demo tenant assumptions before production seed policy |
| 2026-05-21 | Execution priority | MandirMitra live-readiness first | Platform owner direction: complete MandirMitra to live parity after the minimum ERP/accounting foundation, then move to GruhaMitra because both legacy frontends are already live | Keep broad MitraBooks business work behind the MandirMitra live-ready gate |
| 2026-05-21 | Prior planning recap | Captured in PRD workflow | Earlier planning sessions established MitraBooks as the accounting base, MandirMitra first, GruhaMitra second, and full MitraBooks business ERP after both are live | Keep this sequence visible in PRD, gap matrix, and E2E docs |
| 2026-05-21 | MandirMitra Stage 3 smoke | Automated runner and checklist added | `python scripts\mandirmitra_stage3_smoke.py` passed compile checks and 119 focused tests; manual/live checklist added at `docs/operations/MANDIRMITRA_STAGE3_SMOKE_CHECKLIST.md` | Complete remaining live browser checks for public payment, exceptions, audit trace, and deployment readiness |
| 2026-05-21 | MandirMitra public payment live smoke | Backend/API live smoke passed locally | Public temple selector, UPI config/intent, no-login public donation submission, staff verification, correction, rejection, audit trace, receipt PDF text, Trial Balance, I&E, R&P, Balance Sheet, drill-down, and voucher detail were verified locally | Complete visual browser pass in ERP shell; Playwright/browser automation was unavailable in this session |
| 2026-05-21 | MandirMitra ERP browser smoke | Passed locally | `python scripts\mandirmitra_stage3_browser_smoke.py` verified MandirMitra mode, module context, Public Payments, Receipts, and Trial Balance in the local ERP shell | Complete deployment-readiness review |
| 2026-05-22 | MandirMitra Panchang workspace | Wired in ERP shell | Panchang now renders as a MandirMitra workspace backed by `/api/v1/panchang/today`; browser smoke verifies Today Panchang and Tithi content | Continue deployment-readiness review and remaining legacy-live workflow gaps |
| 2026-05-22 | MandirMitra deployment-readiness review | Captured | Environment, seed/demo tenant, audit retention, backup/restore, rollback, hundi/fund/cancellation, 80G/FCRA, and devotee privacy gaps are listed in `docs/operations/MANDIRMITRA_DEPLOYMENT_READINESS_REVIEW.md` | Push current batch and review CI/staging before production signoff |
| 2026-05-22 | MandirMitra Reports workspace | Wired in ERP shell | Reports is now separate from Receipts and renders donation category, detailed donation, detailed seva, seva schedule, and recent devotee data | Continue live workflow review for export/print and any legacy-only report variants |
| 2026-05-22 | MandirMitra first live-cut decisions | Captured | Donation, seva, public payment, receipt, Panchang, reports, accounting, and receipt cancellation/reversal are included; Hundi/fund/festival, refund approval/settlement depth, and 80G/FCRA issuance are deferred until gates are implemented and tested | Confirm deployment environment, seed/demo policy, backup/restore, rollback, and CI/staging |
| 2026-05-22 | MandirMitra sponsorship accounting | Superseded by 2026-07-13 local hardening | The original immediate in-kind posting path is replaced locally by pending valuation, distinct maker-checker approval, and append-only inventory receipt/issue movements | Run the guarded two-user demo mutation and complete receipt/browser polish before production signoff |
| 2026-05-22 | MandirMitra receipt cancellation/reversal | Superseded by 2026-07-13 local refund hardening | Immutable receipt reversal remains; full-refund requests now add maker-checker approval/rejection, settlement evidence, settlement-time reversal, audit, report, and CSV export | Run guarded two-user demo mutation; partial refunds and external payout execution remain deferred |
| 2026-05-22 | MandirMitra CI/staging gate | CI and Render green | GitHub CI and Render workflow deployment are green; local demo receipt reversal produced `REV-*`, Trial Balance stayed balanced, and I&E/R&P/Balance Sheet remained consistent | Run staging smoke non-destructively unless a clearly marked demo/test temple tenant is available |
| 2026-05-22 | MandirMitra public payment visibility | Public page linked | ERP Public Payments workspace links to `/mandir-public/` for no-login temple selector, public UPI/config, seva, and donation-category visibility without creating a payment | Add full devotee submission UX only after demo/staging tenant policy is clear |
| 2026-05-22 | MandirMitra demo public payment submission | Passed demo smoke | `/mandir-public/` submitted a demo pending payment; ERP Public Payments showed it; staff verification posted it with dummy UTR/reference; receipt download, reports, balanced Trial Balance, and voucher drill-down passed | Keep live trust public flow visibility-only unless explicitly using a demo/test tenant |
| 2026-05-22 | MandirMitra production signoff | Checklist added | `docs/operations/MANDIRMITRA_PRODUCTION_SIGNOFF.md` records first-live included scope, deferred scope, tenant safety, accounting safety, and pending production gates | Confirm production environment, backup/restore, rollback tag/process, and tenant seed/demo policy before go-live |
| 2026-05-22 | MandirMitra final local browser smoke | Passed | `python scripts\mandirmitra_stage3_browser_smoke.py --api-base http://127.0.0.1:8001` passed with `organization_type=TEMPLE` and enabled modules `accounting`, `audit`, and `temple` | Confirm CI/Render for final signoff commit and complete production gates |
| 2026-05-22 | MandirMitra production gates | Partially confirmed | Production DB/JWT/app-key/bootstrap/PDF fallback and tenant safety policies are confirmed; production access must use real admin email with no shared default password | Finalize MitraBooks ERP production frontend URL, backup/restore setup, and release tag/rollback execution |
| 2026-05-22 | MandirMitra staging smoke | Non-destructive checks passed | Login/module context, tabs, receipt preview/download, Panchang, reports, balanced accounting reports, and public no-login UPI/config visibility were checked successfully; no mutation was performed on real trust data | Enable the explicit Mandir demo bootstrap tenant with demo UPI/config before destructive staging checks |
| 2026-05-21 | Platform owner, audit, tenant entitlements | Implemented locally; not a pending uncommitted batch | Platform-owner dashboard, entitlements, and audit event listing are in this workspace with route-contract coverage | Super-admin browser E2E for the owner dashboard |
| 2026-05-21 | MitraBooks business parties and typed vouchers | Implemented locally; not production-ready | `/api/v1/business/parties` and `/api/v1/business/vouchers` with frontend, audit, and route contracts. Later phases added invoices, bills, notes, allocation, GST preparation, inventory, BRS, MIS | Production signoff; see 2026-09-10 row |

## Target State

Move to two deployable frontend experiences:

| Frontend | Scope |
| --- | --- |
| MitraBooks Unified ERP | GruhaMitra, MandirMitra, MitraBooks business/professional workflows |
| LegalMitra | Legal workflow and RAG product experience |

The unified MitraBooks frontend should dynamically show modules based on organization type, subscription plan, user role, and feature access.

## Strategic Goals

- Reduce duplicated accounting UI.
- Keep one shared accounting engine.
- Treat MitraBooks as the shared accounting engine and ERP host. Business ERP slices through Phase 5 reporting are **live**. MandirMitra demo-tenant mutation and remaining Gruha workflows still need signoff before calling those product cuts complete.
- Keep tenant and product isolation explicit.
- Allow each organization to activate only relevant modules.
- Preserve brand-specific terminology where it improves user experience.
- Keep LegalMitra separate because its workflows are not primarily accounting ERP workflows.
- Validate E2E stage by stage: LegalMitra baseline, MitraBooks ERP core, MandirMitra, GruhaMitra, then combined ERP regression.
- Current execution priority: production live-ready still requires MandirMitra demo-tenant mutation, then remaining GruhaMitra ERP workflows. Local MitraBooks business slices must not be described as production. GST/TDS stay preparation until a compliance review is signed.

## Active Delivery Workflow

This workflow preserves the project direction agreed in prior planning sessions:

1. Keep LegalMitra stable because it is already live.
2. Use MitraBooks as the base accounting engine, module shell, tenant/app-context layer, and financial reporting foundation.
3. Complete MandirMitra inside that MitraBooks foundation and make it live-ready like LegalMitra.
4. After MandirMitra is live-ready and deployment checks pass, complete GruhaMitra inside the same MitraBooks foundation.
5. MitraBooks business ERP slices (parties, vouchers, sales, purchases, GST preparation, inventory, cash AR/AP, MIS, exports, CA books) are **live** through Phase 5 reporting. Remaining delivery is signoff and unfinished work: hosted mutation reconfirm, Mandir demo-tenant mutation, GST/TDS CA filing signoff, remaining Gruha workflows, then optional Phase 4 AR/AP netting.

Scope control:

- MandirMitra and GruhaMitra production live-ready still outrank new business ERP features.
- Do not describe local business slices, GST preparation reports, or integration config shells as production, live filing, or live bank.
- Do not let optional Phase 4 netting or deferred IRP/e-way work jump Mandir/Gruha signoff.

## Organization Types

Use these canonical values:

| organization_type | Primary frontend | Default modules |
| --- | --- | --- |
| `HOUSING` | MitraBooks Unified ERP | `housing`, `accounting`, `audit` |
| `TEMPLE` | MitraBooks Unified ERP | `temple`, `accounting`, `audit` |
| `BUSINESS` | MitraBooks Unified ERP | `business`, `accounting`, `gst`, `inventory`, `audit` |
| `PROFESSIONAL` | MitraBooks Unified ERP | `professional`, `accounting`, `billing`, `audit` |
| `LEGAL` | LegalMitra | `legal`, `rag`, `compliance`, `legal_ai`, `audit` |

## Functional Requirements

### Shared Platform

- Tenant onboarding and lifecycle.
- Platform owner dashboard for cross-module onboarding status, pending approvals, subscription status, module enablement, and operational KPIs.
- User and role management.
- App-key validation.
- Module registry.
- Feature/module access enforcement.
- Audit log.
- Subscription and plan readiness.

The platform owner dashboard is the review and control layer. It must not replace module-wise onboarding. LegalMitra, MandirMitra, GruhaMitra, and MitraBooks users should start onboarding from their module context, while the platform owner can review payment status, verify submitted documents, approve, reject, request correction, enable modules, and inspect subscription state centrally.

Initial read-only API contract:

- `GET /api/v1/platform-owner/dashboard`
- Access: `super_admin` only.
- Response sections: onboarding summary, tenant summary, subscription summary, app status, module status, pending approvals, recent onboarding requests, and recent tenants.

Initial approval actions reuse existing super-admin onboarding endpoints:

- `PATCH /api/v1/onboarding-requests/{request_id}/payment`
- `PATCH /api/v1/onboarding-requests/{request_id}/verification`
- `POST /api/v1/onboarding-requests/{request_id}/approve`
- `POST /api/v1/onboarding-requests/{request_id}/reject`
- UI action buttons must be shown only in the Platform Owner context and must refresh the dashboard after completion.
- Approval must require payment received or verified, verified documents, and create or update tenants using the onboarding `app_key` to derive `organization_type`, default `enabled_modules`, and `app_keys`.

Initial tenant entitlement action:

- `PATCH /api/v1/tenants/{tenant_id}/entitlements`
- Access: `super_admin` only.
- Supported fields: `subscription_plan`, `enabled_modules`.
- Module updates must validate module key, tenant `organization_type`, and tenant app keys.
- Platform Owner UI may expose this as an entitlement action on tenant rows and must refresh the dashboard after completion.

Initial tenant lifecycle action:

- `PATCH /api/v1/tenants/{tenant_id}/status`
- Access: `super_admin` only.
- Supported statuses: `active`, `inactive`.
- Platform Owner UI may expose this alongside entitlement controls so subscription, module enablement, and tenant lifecycle changes remain auditable and centralized.

### Accounting Engine

- Chart of Accounts.
- Journal entry posting.
- Double-entry validation.
- Strict accounting equation enforcement: `Assets = Liabilities + Equity`.
- Modern account type behavior for Assets, Liabilities, Equity, Revenue, and Expenses.
- Traditional golden-rule support for Real, Personal, and Nominal accounts.
- Atomic posting of every journal entry.
- Immutable append-only posted ledger.
- High-precision amount handling with fixed decimals or integer minor units; no floating-point money.
- Ledger.
- Trial Balance.
- Profit and Loss.
- Balance Sheet.
- Income and Expenditure.
- Receipts and Payments.
- Report drill-down from month to week to day to voucher through shared accounting journals, app-scoped by `X-App-Key`.
- GST/TDS readiness.
- Idempotency for financial posting endpoints.

### Accounting Engine Non-Negotiables

The shared accounting engine must strictly follow double-entry accounting:

- Every financial transaction must have equal debits and credits.
- Validate `sum(debits) - sum(credits) = 0` before commit.
- Wrap debit and credit posting in one database transaction.
- Posted entries must not be edited or deleted.
- Corrections must use reversing or adjusting entries.
- Amounts must use high-precision storage, never floating-point types.

Modern account behavior:

| Account type | Debit | Credit |
| --- | --- | --- |
| Asset | Increase | Decrease |
| Liability | Decrease | Increase |
| Equity | Decrease | Increase |
| Revenue | Decrease | Increase |
| Expense | Increase | Decrease |

Traditional golden rules:

| Traditional type | Rule |
| --- | --- |
| Real accounts | Debit what comes in, credit what goes out |
| Personal accounts | Debit the receiver, credit the giver |
| Nominal accounts | Debit all expenses and losses, credit all incomes and gains |

### GruhaMitra Module

- Flats, towers, residents.
- Maintenance billing and collection.
- Parking and vendor payments.
- Complaint/service request lifecycle.
- Society accounting reports.

### MandirMitra Module

- Module-wise temple/trust onboarding.
- Donations and receipts.
- Cash and in-kind sponsorships for Annadanam, festivals, decoration, lighting, pooja/ritual articles, and other event purposes.
- Seva booking.
- Hundi collection.
- Devotee database.
- Trust/corpus/festival accounting.
- 80G readiness where applicable.

Active completion target:

- MandirMitra must be completed to live-ready parity before GruhaMitra migration starts.
- Live-ready means the legacy-live MandirMitra workflows work through the unified backend/ERP shell with tenant isolation, app-key isolation, receipt correctness, accounting correctness, auditability, and a repeatable smoke/E2E checklist.
- Minimum supporting MitraBooks ERP work is allowed only where it is required for MandirMitra accounting, module access, reports, or shell navigation.
- Broad MitraBooks business module work remains secondary until the MandirMitra live-ready gate is green.

Initial MitraBooks ERP shell integration:

- Mandir mode uses `X-App-Key: mandirmitra` for legacy-compatible MandirMitra routes while the unified ERP shell remains the host experience.
- Live dashboard reads `GET /api/v1/dashboard/stats` for donation and seva summaries.
- Public devotee payment must remain available without login.
- Public devotee flow: select temple/trust, select donation or seva, enter amount/details, and pay using that temple/trust's configured UPI QR/payment instructions.
- Real public-enabled trusts may be used only for non-destructive public payment visibility checks. Public payment mutation tests must use a clearly marked demo/test temple tenant with demo UPI/config values.
- Pending public payment review reads `GET /api/v1/public-payments?status=pending`.
- Verification action calls `PATCH /api/v1/public-payments/{payment_id}/verify`, which must create the donation or seva record, generate receipt data, and post the accounting entry only after staff verification.
- Current shell verification captures UTR/reference, payment date, and optional bank account selection before posting.
- Current shell receipt action downloads the protected receipt PDF returned by the verification response using the tenant access token and `X-App-Key: mandirmitra`.
- Verification requires a UTR/reference before posting and rejects unsafe reference text.
- Current shell receipt preview fetches the protected receipt PDF with the tenant access token and renders it in a modal preview before or alongside download.
- Current shell receipt history reads recent donation and seva booking receipts from `GET /api/v1/donations?limit=8` and `GET /api/v1/sevas/bookings?limit=8`, with preview/download actions for each receipt.
- Current shell donation and seva panels show recent donation rows and recent seva booking rows with receipt actions where available.
- Current shell payment exception queue reads `GET /api/v1/public-payments/exceptions?older_than_hours=24` and flags stale pending payments, invalid amounts, missing phone data, invalid payment type, and missing donation/seva purpose data.
- Current shell exception resolution supports rejecting an unverified public payment through a structured rejection dialog backed by `PATCH /api/v1/public-payments/{payment_id}/reject`, retaining rejection reason, actor, timestamp, and audit event.
- Current shell exception correction supports repairing unverified public payment amount, phone, payment type, and donation/seva purpose through `PATCH /api/v1/public-payments/{payment_id}/correction`, retaining actor, timestamp, and audit event.
- Current backend list groundwork supports `offset`, text search, and date filtering on donation/seva booking lists, plus `payment_mode` for donations and `status` for seva bookings.
- Current shell donation and seva list panels expose lightweight search, date, mode/status filters, and previous/next paging over the existing backend list parameters.
- Current shell exposes focused MandirMitra workspace views for overview, donations, sevas, public payments, exceptions, and receipts while reusing the same tenant/app-scoped live data.
- Current shell MandirMitra side navigation switches supported module links into the focused workspace views and keeps the active navigation state aligned.
- Current public payment list supports `limit`, `offset`, status, text search, and payment type filters; the shell exposes these controls in the public payment review panel.
- Current public payment exception list supports `limit`, `offset`, reason, status, text search, and payment type filters; the shell exposes these controls in the exception review panel.
- Current shared accounting report drill-down supports month, week, day, and voucher levels through `GET /api/v1/accounting/reports/drilldown`; voucher rows can open `GET /api/v1/accounting/reports/vouchers/{journal_id}` to inspect debit/credit lines. MitraBooks ERP uses the active `X-App-Key` so the same report panel applies to MitraBooks, MandirMitra, and GruhaMitra.
- Current local MandirMitra donation posting distinguishes cash sponsorship from in-kind support. In-kind donations remain `pending_valuation` until a different authorized actor approves a fixed-precision value; approval then posts the balanced tenant/app-scoped MitraBooks journal. Inventory-enabled consumables also create a valued append-only stock receipt.
- Current MandirMitra quick-entry donation form captures cash/in-kind type, event/festival, item name, item type, quantity, and valuation basis; donation reports surface this metadata for review.
- Current MandirMitra receipt history supports cancellation/reversal actions for donation and seva receipts; cancellation posts a linked reversal journal and records reason, actor, timestamp, refund mode, and refund reference without editing the original receipt amount/category/seva details.
- Gap: no major public payment verification shell gap remains in the initial MandirMitra dashboard slice; future work should expand these dashboard panels into dedicated routed full-list screens with stable URL state, exports, and richer audit drill-down.
- Gap: the valuation, stock issue/consumption, and event/fund subledger foundations are implemented locally, but the guarded two-user demo mutation and production signoff have not yet run. Receipt/browser polish and richer voucher drill-down remain open.
- Current local refund operations provide a tenant/app-scoped full-refund queue, distinct maker-checker approval/rejection, approved-pending-settlement state, mandatory payout evidence, settlement-time journal reversal, retry-safe persistence, audit events, report, and CSV export.
- Gap: the guarded two-user demo mutation and production signoff have not run. Partial refunds and external payment-provider execution remain deferred.

#### 2026-07-13 fund-accounting update

The fund-accounting subledger foundation is implemented locally. New fund masters receive tenant/app-scoped accounting cost-centre dimensions; designated donation income is tagged to the fund; maker-checker fund transfers and opening balances post balanced, idempotent, reversible journals; transfer approval denies a negative source-fund balance; and fund reporting derives brought-forward, opening-entry, income, expense, transfer, closing, and as-of balances from accounting-backed activity. The in-kind gate adds pending valuation, distinct maker-checker approval, server-derived weighted-average issue value, negative-stock denial, append-only receipt/issue/reversal movements, and cross-store accounting compensation. Guarded two-user runtime mutation, receipt/browser polish, and richer voucher drill-down remain gaps.

### MitraBooks Business Module

Current state:

- Shared accounting APIs support journal posting, reversal, ledger, trial balance, profit and loss, receipts/payments, balance sheet, and report drill-downs.
- `/api/v1/business` is the target API surface. Legacy `mitrabooks_compat` routes remain compatibility-only.
- Parties: tenant/app/entity-scoped create/list/get/update/deactivate. `party_type` is `customer | vendor | both`. Live balances come from party-ledger/outstanding reports, not Mongo party fields.
- Typed vouchers: payment, receipt, contra, and journal post through the accounting service with generated numbers, idempotency, listing, detail, and reversal.
- Sales invoices and purchase bills: draft or pending approval, approve-to-post, compensation on domain persistence failure, cancellation reversal. Invoice PDF is posted-only. Dedicated bill PDF is not implemented.
- Credit and debit notes: GL posting, source-document linkage, compensation, cancellation reversal. Production print/export templates remain open.
- Cash AR/AP: open-item allocation (receipts→invoices, payments→bills), FIFO suggestions, statements, dunning, ageing. Allocation writes Mongo matching only and posts no new journal. Cross-side AR/AP netting / set-off is **not implemented**.
- GST/TDS: GSTIN, place of supply, HSN/SAC, period locks, RCM, composition, GSTR-1/3B/2B preparation, CMP-08/GSTR-4 route shape, GST settlement preview/post/reverse, TDS register. These are **preparation/reporting**, not production filing.
- Inventory: opt-in, item master, stock register, weighted-average periodic valuation, issue/adjustment, closing-stock journal. Multi-location and batch/serial remain deferred.
- Banking: CSV import, match/unmatch, bank/cash book. Live bank API sync is deferred.
- Fixed assets, dimensions (including branch-to-cost-centre P&L), opening balances, year-end close, MIS, data health, governed exports, and Tally XML **masters** proof exist locally. Voucher-level Tally XML and production signoff remain open.
- CA practice: per-client `accounting_entity_id` books, book switch via `X-Accounting-Entity-ID`, document inbox, token-based invites. Staff assignment per book and pricing client caps remain open.
- Evidence: local Phase 3 destructive mutation (2026-07-03), Gruha billing gate (2026-07-17), Phase 5 MIS/export and inventory/banking read gates (2026-07-18), combined read-only regression (2026-07-18). Hosted destructive mutation **reconfirm** after credential drift is still required.

Target state:

- Production-ready business/professional workflows with compliance-reviewed GST preparation, operator signoff, and print/export polish.
- Optional later: AR/AP netting document (Dr AP / Cr AR with applications on invoices and bills; GST/TDS on original documents unchanged).
- Professional-services labels may reuse the same party/invoice engine; that product decision is still open.

Gap:

- Production signoff, hosted destructive mutation reconfirm, GST/TDS human compliance review, print/PDF polish, CA staff-per-book, opening/year-end operator maker-checker, and remaining Gruha workflows.
- AR/AP netting is a planned Phase 4 completeness item, not current product.
- Do not claim live GST filing, e-invoice IRP, e-way bill API, bank payout execution, or OCR auto-post.

Deferred scope:

- Production GST filing integrations, e-invoice/e-way bill APIs, bank sync, OCR/AI auto-posting, AI MIS narration, desktop SQLite, and production data migration remain out of immediate scope until a named workstream exists.

Detailed MitraBooks ERP scope, legacy-plan decisions, rejected desktop-era assumptions, and implementation phases are maintained in [MitraBooks ERP Gap Matrix](MITRABOOKS_ERP_GAP_MATRIX.md).

### LegalMitra

- Case records.
- Legal documents.
- RAG with source attribution.
- Compliance calendar.
- Claude Legal Counsel provider-gated research/drafting support, with human review and source attribution.
- Client billing integration where needed.

Detailed LegalMitra enhancement scope — current vs target vs gap, multi-persona Professional Intelligence Platform direction, stage gates, and Not Now list — is maintained in [LegalMitra Professional Intelligence PRD](LEGALMITRA_PROFESSIONAL_INTELLIGENCE_PRD.md). Implementation detail (stack, modules, code surfaces, preflight) is in [LegalMitra Architecture Specification](../architecture/LEGALMITRA_ARCHITECTURE_SPEC.md). Those documents must not override LegalMitra separation from MitraBooks ERP, Claude production gating, or Stage 1 E2E baseline rules in this PRD and `AGENTS.md`.

## Non-Functional Requirements

- Tenant isolation on every query.
- Accounting immutability and auditability.
- API-first behavior.
- Modular monolith structure.
- Clear migration path.
- No live frontend disruption during migration.

## Explicit Non-Goals for Foundation PR

The foundation PR is complete. These remain architecture non-goals for unified delivery:

- Do not merge all frontends.
- Do not redesign the entire UI.
- Do not rewrite the accounting engine.
- Do not migrate production data.
- Do not create microservices.
- Do not change live app repositories.
- Do not implement InvestMitra, FinceptTerminal, or Zerodha Kite MCP in SanMitra unified backend.
- Do not enable Claude Legal Counsel for production tenants without confidentiality, retention, source-attribution, and human-review approval.

## Strategic Integration Roadmap

LegalMitra provider integrations remain planned incremental enhancements, not first-PR scope. InvestMitra integrations are out of SanMitra unified scope and may be handled only in a separate personal-use workstream.

### LegalMitra: Claude Legal Counsel

Purpose:

- Use Claude Legal Counsel as an optional LegalMitra assistant layer for legal drafting, review, research workflow, summarization, and document analysis.

Boundary:

- Preserve client confidentiality.
- Maintain source attribution.
- Do not replace lawyer/user review.
- Clearly distinguish retrieved legal source material from AI-generated analysis.
- Support Indian legal workflow and jurisdiction metadata before production use.
- Current implementation status: backend provider path is implemented for `/api/v1/legal-research`; production use remains gated by environment configuration and E2E approval.

## Integration Sequence

1. Document capability, licensing, security, and compliance requirements.
2. Create adapter interfaces with no UI dependency.
3. Build read-only proof of concept.
4. Add audit logging and permission checks.
5. Add frontend read-only research/legal-assistant screens.
6. Add human-review workflows and disclaimers.
7. Enable per tenant/plan only after security and workflow review.
