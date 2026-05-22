# SanMitra Unified Platform PRD

## Purpose

Create a clear foundation for merging the accounting-heavy product experiences into one maintainable ERP platform while preserving SanMitra's product brands.

## Product Brands

- GruhaMitra: housing societies, apartments, RWAs, gated communities.
- MandirMitra: temples, trusts, NGOs, donation and seva workflows.
- MitraBooks: businesses, SMEs, professionals, retailers, accounting users.
- LegalMitra: legal research, legal workflow, compliance.
- InvestMitra: portfolio tracking and investment intelligence.

## Current State

The reference backend at `D:\sanmitra-backend` already provides a unified backend foundation:

- One FastAPI backend.
- Modular monolith structure.
- Shared accounting engine.
- PostgreSQL for accounting records.
- MongoDB for tenant, user, and domain records.
- Tenant middleware scaffold.
- RBAC foundation.
- `X-App-Key` routing for product context.
- COA mapping APIs.
- MandirMitra donation accounting flow.
- GruhaMitra maintenance accounting flow.
- LegalMitra and InvestMitra tenant-scoped route stubs.

Current limitation: accounting-oriented frontends are still treated as separate product applications, creating duplicate UI and support effort.

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
| 2026-05-22 | MandirMitra sponsorship accounting | Backend posting and basic UI covered | Cash sponsorship now credits Sponsorship Income; valued in-kind Annadanam credits In-Kind Sponsorship Income and debits expense when inventory is off or inventory when inventory is on; precious articles classify to temple asset accounts; quick-entry captures event/item/quantity/valuation basis; focused tests pass | Add valuation approval, stock consumption, and event/fund subledger reports after first live cut |
| 2026-05-22 | MandirMitra receipt cancellation/reversal | Backend and ERP action covered | Donation and seva receipts can be reversed from the ERP receipt list; backend keeps original values, creates linked reversal journal, records reason/actor/timestamp/refund metadata, and focused tests pass | Add richer refund approval queue, payout settlement status, and refund exports after first live cut |
| 2026-05-22 | MandirMitra CI/staging gate | CI and Render green | GitHub CI and Render workflow deployment are green; local demo receipt reversal produced `REV-*`, Trial Balance stayed balanced, and I&E/R&P/Balance Sheet remained consistent | Run staging smoke non-destructively unless a clearly marked demo/test temple tenant is available |
| 2026-05-22 | MandirMitra public payment visibility | Public page linked | ERP Public Payments workspace links to `/mandir-public/` for no-login temple selector, public UPI/config, seva, and donation-category visibility without creating a payment | Add full devotee submission UX only after demo/staging tenant policy is clear |
| 2026-05-21 | Platform owner, audit, tenant entitlements | Pending review | Local source/tests/docs exist but remain uncommitted in the current working tree | Review and commit as a focused foundation batch if accepted |
| 2026-05-21 | MitraBooks business parties and typed vouchers | Pending review | Local source/tests exist under `/api/v1/business` but remain uncommitted in the current working tree | Review separately as Phase 2 business work |

## Target State

Move to three frontend experiences:

| Frontend | Scope |
| --- | --- |
| MitraBooks Unified ERP | GruhaMitra, MandirMitra, MitraBooks business/professional workflows |
| LegalMitra | Legal workflow and RAG product experience |
| InvestMitra | Investment and portfolio product experience |

The unified MitraBooks frontend should dynamically show modules based on organization type, subscription plan, user role, and feature access.

## Strategic Goals

- Reduce duplicated accounting UI.
- Keep one shared accounting engine.
- Treat MitraBooks as the shared accounting engine and ERP host first; full MitraBooks business ERP scope is a later expansion after MandirMitra and GruhaMitra are completed and deployed live.
- Keep tenant and product isolation explicit.
- Allow each organization to activate only relevant modules.
- Preserve brand-specific terminology where it improves user experience.
- Keep LegalMitra and InvestMitra separate because their workflows are not primarily accounting ERP workflows.
- Validate E2E stage by stage: LegalMitra baseline, MitraBooks ERP core, MandirMitra, GruhaMitra, combined ERP regression, then InvestMitra.
- Current execution priority: after the minimum MitraBooks ERP/accounting foundation needed for tenant context, modules, and postings, finish MandirMitra to live-ready parity before expanding GruhaMitra. Broad MitraBooks business features must not distract from the MandirMitra live-ready gate.

## Active Delivery Workflow

This workflow preserves the project direction agreed in prior planning sessions:

1. Keep LegalMitra stable because it is already live.
2. Use MitraBooks as the base accounting engine, module shell, tenant/app-context layer, and financial reporting foundation.
3. Complete MandirMitra inside that MitraBooks foundation and make it live-ready like LegalMitra.
4. After MandirMitra is live-ready and deployment checks pass, complete GruhaMitra inside the same MitraBooks foundation.
5. Only after MandirMitra and GruhaMitra are completed and deployed live, expand the larger MitraBooks business ERP roadmap: parties, vouchers, sales, purchases, GST, inventory, AR/AP, MIS, exports, and CA/bookkeeper workflows.

Scope control:

- MitraBooks accounting work is in scope now when it is needed by MandirMitra or later GruhaMitra.
- MitraBooks business ERP work is deferred unless it fixes a shared accounting, reporting, tenant-context, audit, or route-contract gap needed for MandirMitra/GruhaMitra live readiness.
- Do not let Phase 2 business modules become the active delivery track before MandirMitra and GruhaMitra are live.

## Organization Types

Use these canonical values:

| organization_type | Primary frontend | Default modules |
| --- | --- | --- |
| `HOUSING` | MitraBooks Unified ERP | `housing`, `accounting`, `audit` |
| `TEMPLE` | MitraBooks Unified ERP | `temple`, `accounting`, `audit` |
| `BUSINESS` | MitraBooks Unified ERP | `business`, `accounting`, `gst`, `inventory`, `audit` |
| `PROFESSIONAL` | MitraBooks Unified ERP | `professional`, `accounting`, `billing`, `audit` |
| `LEGAL` | LegalMitra | `legal`, `rag`, `compliance`, `legal_ai`, `audit` |
| `INVESTMENT` | InvestMitra | `investment`, `portfolio`, `investment_research`, `broker_research`, `audit` |

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

The platform owner dashboard is the review and control layer. It must not replace module-wise onboarding. MandirMitra, GruhaMitra, and MitraBooks users should start onboarding from their module context, while the platform owner can review, approve, reject, request correction, enable modules, and inspect subscription state centrally.

Initial read-only API contract:

- `GET /api/v1/platform-owner/dashboard`
- Access: `super_admin` only.
- Response sections: onboarding summary, tenant summary, subscription summary, app status, module status, pending approvals, recent onboarding requests, and recent tenants.

Initial approval actions reuse existing super-admin onboarding endpoints:

- `POST /api/v1/onboarding-requests/{request_id}/approve`
- `POST /api/v1/onboarding-requests/{request_id}/reject`
- UI action buttons must be shown only in the Platform Owner context and must refresh the dashboard after completion.
- Approval must create or update tenants using the onboarding `app_key` to derive `organization_type`, default `enabled_modules`, and `app_keys`.

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
- Parlathya Prathishtana remains a known working reference example for the public payment and temple/trust selection flow.
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
- Current MandirMitra donation posting distinguishes cash sponsorship, valued in-kind sponsorship, in-kind donations, directly consumed event support, Annadanam consumables, and precious temple articles using tenant-scoped MitraBooks accounts. Consumable in-kind accounting follows the temple inventory setting: expense when inventory is off and inventory asset when it is on.
- Current MandirMitra quick-entry donation form captures cash/in-kind type, event/festival, item name, item type, quantity, and valuation basis; donation reports surface this metadata for review.
- Current MandirMitra receipt history supports cancellation/reversal actions for donation and seva receipts; cancellation posts a linked reversal journal and records reason, actor, timestamp, refund mode, and refund reference without editing the original receipt amount/category/seva details.
- Gap: no major public payment verification shell gap remains in the initial MandirMitra dashboard slice; future work should expand these dashboard panels into dedicated routed full-list screens with stable URL state, exports, and richer audit drill-down.
- Gap: valuation approval, in-kind stock issue/consumption, and event/fund subledger reporting need a later dedicated slice before calling sponsorship management feature-complete.
- Gap: refund approval queue, payout settlement status, and refund export/reporting remain later work.

### MitraBooks Business Module

Current state:

- Shared accounting APIs already support journal posting, reversal, ledger, trial balance, profit and loss, receipts/payments, balance sheet, and report drill-downs.
- A small Phase 2 backend slice is being introduced under `/api/v1/business` for tenant/app-key scoped parties and typed vouchers.
- Current party master work includes party creation, listing, lookup, profile update, and soft deactivation. Party profile updates do not mutate opening or current balances.
- Current typed voucher work includes generated payment/receipt/contra/journal voucher numbers, idempotency-key reuse, voucher listing, voucher detail lookup, and reversal posting through the shared accounting reversal service.
- Current party and voucher lifecycle actions write best-effort tenant-scoped audit events with old/new snapshots where applicable.
- Current audit backend exposes `GET /api/v1/audit/events` for tenant-scoped, app-key scoped audit event listing with filters for entity type, entity id, and action.
- Legacy compatibility routes still exist for older MitraBooks-style parties, invoices, and transactions, but they are not the target API surface for new business workflow work.

Target state:

- Customer/vendor/party master for `BUSINESS` tenants.
- Typed payment, receipt, contra, and journal voucher APIs as facades over the shared accounting service.
- Sales and purchase invoices with immutable GL posting links.
- GST invoice setup and reporting readiness.
- Inventory, AR/AP ageing, business reports, MIS, data health, and export workflows in later phases.

Gap:

- Party and typed voucher contracts have backend route-contract coverage, lifecycle audit events, and audit event query support; they still need frontend integration, frontend manifest coverage, audit UI expansion, voucher cancel/update policy, reversal UX, and browser E2E.
- Invoice posting, GST, inventory, AR/AP, MIS, exports, and payroll readiness are planned but not yet implemented in the target `/api/v1/business` module.
- Professional-services workflows may reuse the party/invoice engine with different labels, but that is not decided yet.

Deferred scope:

- Production GST filing integrations, e-invoice/e-way bill APIs, bank sync, OCR/AI auto-posting, desktop SQLite, and production data migration remain out of immediate scope.

Detailed MitraBooks ERP scope, legacy-plan decisions, rejected desktop-era assumptions, and implementation phases are maintained in [MitraBooks ERP Gap Matrix](MITRABOOKS_ERP_GAP_MATRIX.md).

### LegalMitra

- Case records.
- Legal documents.
- RAG with source attribution.
- Compliance calendar.
- Claude Legal Counsel provider-gated research/drafting support, with human review and source attribution.
- Client billing integration where needed.

### InvestMitra

- Holdings.
- Asset classes.
- Portfolio performance.
- XIRR/P&L calculations.
- Investment insights.
- FinceptTerminal research integration readiness.
- Zerodha Kite MCP research integration readiness.

InvestMitra integrations are for investment research only. They must not place, modify, cancel, or automate trades.

## Non-Functional Requirements

- Tenant isolation on every query.
- Accounting immutability and auditability.
- API-first behavior.
- Modular monolith structure.
- Clear migration path.
- No live frontend disruption during migration.

## Explicit Non-Goals for Foundation PR

- Do not merge all frontends.
- Do not redesign the entire UI.
- Do not rewrite the accounting engine.
- Do not migrate production data.
- Do not create microservices.
- Do not change live app repositories.
- Do not implement FinceptTerminal production integration.
- Do not implement Zerodha Kite MCP production integration.
- Do not enable Claude Legal Counsel for production tenants without confidentiality, retention, source-attribution, and human-review approval.

## Strategic Integration Roadmap

These integrations were discussed earlier and are now reserved in the product roadmap. They are planned incremental enhancements, not first-PR scope.

### InvestMitra: FinceptTerminal

Purpose:

- Use FinceptTerminal as a research and analytics source for InvestMitra.
- Support equity research, macro/economic research, portfolio analytics, screeners, and AI-assisted research summaries.

Boundary:

- Research only.
- No broker execution.
- No order placement, modification, cancellation, or automated trading.
- Licensing must be reviewed before any internal or commercial use.

### InvestMitra: Zerodha Kite MCP

Purpose:

- Use Zerodha Kite MCP only for authenticated, user-authorized market and portfolio context.
- Support holdings-aware research, watchlist enrichment, instrument lookup, quotes, and historical data where allowed.

Boundary:

- Read-only research use.
- Disable or omit all order placement tools.
- No financial advice framed as guaranteed outcome.
- Broker credentials and tokens must never be logged.

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
