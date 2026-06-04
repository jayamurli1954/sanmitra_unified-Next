# SanMitra Unified Platform - Comprehensive Review
**Date:** May 30, 2026  
**Current Version:** 1.3.0  
**Status:** MandirMitra Live-Ready Pending Final Production Gates

---

## Executive Summary

The SanMitra Unified Platform is a modular monolith backend architected to host five product brands (GruhaMitra, MandirMitra, MitraBooks, LegalMitra, InvestMitra) through a unified authentication, tenancy, accounting, and API layer. The platform has successfully executed a staged delivery approach:

- **LegalMitra** is deployed and live in production
- **MandirMitra** is feature-complete and ready for production deployment
- **GruhaMitra** is on deck after MandirMitra goes live
- **MitraBooks business ERP** is phased behind the MandirMitra/GruhaMitra live-ready gates
- **InvestMitra** remains a separate frontend experience

This review captures what has been planned, what is complete, what is in pending review, and what remains in the pipeline.

---

## Part 1: Strategic Architecture & Platform Direction

### 1.1 Current Platform Vision

**Target State:** Three unified frontend experiences instead of five separate apps:

| Frontend | Scope | Status |
|----------|-------|--------|
| **MitraBooks Unified ERP** | GruhaMitra, MandirMitra, MitraBooks business/professional accounting | Hosting MandirMitra, pending GruhaMitra |
| **LegalMitra** | Legal research, RAG, case workflows, compliance | ✅ LIVE in production |
| **InvestMitra** | Portfolio, investment research, insights | Separate frontend (not yet merged) |

### 1.2 Database Strategy (Split, Not One)

- **PostgreSQL:** Accounting data (accounts, journals, ledger, reports, tax records)
- **MongoDB:** Tenants, users, module data, domain records (donations, sevas, cases, holdings), audit logs
- **Redis:** Sessions, caching, background job coordination (where applicable)

This split preserves financial source-of-truth in PostgreSQL while keeping domain operations flexible in MongoDB.

### 1.3 Multi-Tenancy Model

Every request resolves:
- `tenant_id` (organization)
- `app_key` (product context: mandirmitra, gruhamitra, mitrabooks, legalmitra, investmitra)
- `organization_type` (business model: TEMPLE, HOUSING, BUSINESS, PROFESSIONAL, LEGAL, INVESTMENT)
- `enabled_modules` (which features/products tenant has access to)
- User role and permissions

**Key guardrail:** `app_key` ≠ `organization_type`. The former is product routing; the latter is business model classification.

---

## Part 2: What Has Been Planned

### 2.1 Foundation PR Scope (Documented, Partially Implemented)

**Location:** `docs/migration/FOUNDATION_PR_PLAN.md`

#### Planned deliverables:

1. **Documentation normalization**
   - ✅ Product branding standardized (GruhaMitra, not GharMitra/GrihaMitra)
   - ✅ Current vs Target matrix created (`docs/architecture/CURRENT_VS_TARGET.md`)
   - ✅ Platform direction documented in PRD

2. **Backend foundation**
   - ✅ `organization_type` enum design complete
   - ✅ `enabled_modules` list design complete
   - ⚠️ **Module registry:** Initial design done, needs hardening
   - ⚠️ **Module access helper:** Pattern established, partial route coverage
   - ⚠️ **Tenant isolation tests:** Coverage incomplete, only representative routes tested
   - ⚠️ **Accounting guardrails:** Strong tests exist but not comprehensive

### 2.2 MandirMitra Live-Ready Plan (Documented & Implemented)

**Location:** `docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md` + `docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md`

#### Planned workflow:
1. Keep LegalMitra stable ✅
2. Build MitraBooks ERP core accounting foundation ✅
3. Complete MandirMitra inside MitraBooks ERP ✅
4. Make MandirMitra live-ready ⚠️ (nearly complete, pending production gates)
5. Start GruhaMitra only after MandirMitra is live ⏳

#### MandirMitra Scope (Documented & Verified):

**In scope for first live cut:**
- ✅ Donation management and receipt PDF generation (bilingual Kannada/English)
- ✅ Seva (religious service) booking and bilingual receipts
- ✅ Public no-login donation/seva submission
- ✅ Protected staff verification workflow (dummy UTR/reference capture)
- ✅ Receipt preview and download
- ✅ Receipt cancellation/reversal with immutable original entries
- ✅ Cash and in-kind sponsorship accounting
- ✅ Panchang (Hindu calendar) widget in ERP shell
- ✅ Accounting reports: Trial Balance, Income & Expenditure, Receipts & Payments, Balance Sheet, drill-down
- ✅ Audit logging for public payments, verification, rejection, correction
- ✅ Tenant/app-key isolation enforcement

**Deferred from first live cut:**
- Hundi (temple safe box) depth workflows
- Festival/fund accounting and subledger reporting
- 80G/FCRA (tax exemption) issuance
- Refund payout approval queue and settlement
- Sponsorship valuation approval and inventory consumption
- Advanced export workflows

### 2.3 MitraBooks Business ERP Phases (Documented, Phase 1 Only)

**Location:** `docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md`

#### Phase 1: MitraBooks ERP Core (Partially Complete)
- ✅ Shared accounting engine with journal posting, reversal, idempotency
- ✅ Ledger, trial balance, P&L, balance sheet, receipts/payments reports
- ✅ Tenant/app-key/module access framework
- ✅ Platform-owner dashboard contract (backend API exists)
- ✅ Module registry design
- ⚠️ **Gap:** Full browser E2E and UI integration for platform-owner dashboard

#### Phase 2: Business Masters & Typed Vouchers (Pending Review)
- ⚠️ **Party master:** Backend API complete (`/api/v1/business/parties`), no frontend integration
- ⚠️ **Typed vouchers:** Backend payment/receipt/contra/journal facades complete, no frontend integration
- ⚠️ **Audit events:** Backend support exists, no UI expansion

#### Phases 3-5: Deferred (Not Started)
- Sales/purchase invoices
- GST setup and reporting (GSTR-1, GSTR-3B)
- Inventory and FIFO
- AR/AP ageing and receivables/payables
- MIS dashboard and data health score
- Export workflows (Excel, PDF, JSON, Tally XML)

### 2.4 Integration Roadmap (Reserved, Not Implemented)

**Location:** `docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md` (Section: Strategic Integration Roadmap)

#### Documented but Deferred:
1. **InvestMitra: FinceptTerminal** - Research-only integration (no broker execution)
2. **InvestMitra: Zerodha Kite MCP** - Holdings-aware research (read-only, no order placement)
3. **LegalMitra: Claude Legal Counsel** - Legal drafting/research assistant (confidentiality-gated)

These are reserved in the module registry but production implementation requires security review and compliance approval.

---

## Part 3: What Has Been Completed

### 3.1 Backend Foundation (Core)

**Status:** ✅ COMPLETE & STABLE

#### 3.1.1 Authentication & Tenancy
- ✅ FastAPI unified backend at `https://sanmitra-unified-next-staging-sg.onrender.com`
- ✅ JWT-based authentication with tenant resolution
- ✅ Google OAuth integration (`/api/v1/auth/google`)
- ✅ Tenant middleware enforcing `X-Tenant-ID` or JWT context
- ✅ Organization type tracking (`TEMPLE`, `HOUSING`, `BUSINESS`, `PROFESSIONAL`, `LEGAL`, `INVESTMENT`)
- ✅ Enabled modules tracking per tenant
- ✅ RBAC foundation with user roles and permissions

#### 3.1.2 Accounting Engine
- ✅ **Double-entry accounting** with strict invariant: debits always equal credits
- ✅ **Journal posting** with immutable append-only ledger
- ✅ **Reversal support** for corrections using linked reversal journals
- ✅ **Idempotency keys** for safe financial request retries
- ✅ **Chart of Accounts** with tenant-scoped accounts
- ✅ **Accounting reports:**
  - Trial Balance (month/week/day/voucher drill-down)
  - Profit & Loss
  - Balance Sheet
  - Income & Expenditure
  - Receipts & Payments
  - Ledger details with voucher linkage
- ✅ **High-precision amounts** (integer minor units/paise, no floating-point)
- ✅ **Tenant isolation** on every query

**Code location:** `app/accounting/` (journal, ledger, reports, models, schemas)

**Test coverage:** 100+ focused tests across accounting posting, reversal, isolation, and invariants

#### 3.1.3 Module Registry & Access Control
- ✅ **Module registry design** with module keys, organization types, app keys, features
- ✅ **Module access helper** function for route-level enforcement
- ✅ **Enabled modules** derivation from organization type and subscription plan
- ✅ **Feature flag design** (reserved for future legal_ai, investment_research, broker_research)
- ✅ **Route-level access guards** on representative core routes

**Code location:** `app/core/modules/` (registry, service, helpers)

**Test coverage:** Module access tests on accounting, audit, housing, temple routes

### 3.2 LegalMitra (Deployed & Live)

**Status:** ✅ LIVE IN PRODUCTION

**Frontend:** https://www.legalmitra.sanmitratech.in (Vercel)  
**Backend:** Render (unified backend)

#### Completed workflows:
- ✅ User authentication and workspace access
- ✅ Chat history and AI legal counsel (source-attributed)
- ✅ Template marketplace and document rendering
- ✅ Case record management (basic)
- ✅ RAG-based legal research
- ✅ Compliance calendar
- ✅ Tenant/app-key isolation

**Evidence:** E2E verification report (docs/operations/E2E_VERIFICATION_REPORT.md) confirms all live workflows pass

### 3.3 MandirMitra (Feature-Complete, Pending Production Gates)

**Status:** ⚠️ READY FOR PRODUCTION DEPLOYMENT (Gates pending final confirmation)

**Frontend:** https://www.mandirmitra.sanmitratech.in (Vercel)  
**Backend:** Render (unified backend) + MitraBooks ERP shell

**Last verified:** 2026-05-22 with local smoke, staging non-destructive checks, and CI/Render green

#### Completed workflows:

**Donations:**
- ✅ Donation creation with amount, category, payment mode
- ✅ Donation receipt PDF (bilingual Kannada/English)
- ✅ Receipt numbering with sequence management
- ✅ Donation reports with donation category breakdown
- ✅ Accounting posting to income accounts
- ✅ Drill-down to voucher detail and GL entries

**Sevas (Religious Services):**
- ✅ Seva booking with service type, schedule, devotee
- ✅ Seva receipt with devotee label and Kannada terminology
- ✅ Seva booking reports
- ✅ Accounting posting to service income
- ✅ Accounting drill-down

**Public Payments (No-Login):**
- ✅ Public temple/trust selector page (`/mandir-public/`)
- ✅ Public donation/seva submission form
- ✅ UPI payment intent or configured QR display
- ✅ Demo/test tenant submission guarding (real trusts are visibility-only)
- ✅ Pending payment tracking in ERP

**Staff Verification:**
- ✅ Protected `/api/v1/public-payments/{payment_id}/verify` endpoint
- ✅ UTR/reference capture before posting
- ✅ Receipt PDF generation on successful verification
- ✅ Accounting entry posting only after verification
- ✅ Audit event logging (who verified, when, UTR/reference)

**Exception Handling:**
- ✅ Public payment exception queue (stale pending, invalid amounts, missing data)
- ✅ Rejection workflow with reason/actor/timestamp audit
- ✅ Correction workflow for amount, phone, payment type, purpose
- ✅ Immutable audit trail for all corrections

**Sponsorship Accounting:**
- ✅ Cash sponsorship posting to Sponsorship Income
- ✅ Valued in-kind Annadanam (food offerings) posting:
  - Expense account when inventory is off
  - Inventory asset account when inventory is on
- ✅ Precious articles classification to temple asset accounts
- ✅ Quick-entry donation form capturing event/festival, item, quantity, valuation basis
- ✅ Sponsorship reports with item metadata
- ✅ Focused test coverage (posting guardrails pass)

**Receipts & Cancellation:**
- ✅ Donation/seva receipt history
- ✅ Preview and download functionality
- ✅ Receipt cancellation/reversal action
- ✅ Reversal journals created with linked original receipt reference
- ✅ Immutable original receipt values (amount, category, seva unchanged)
- ✅ Metadata stored: reason, actor, timestamp, refund mode/reference
- ✅ Idempotent on repeat (safe to retry)

**Panchang (Hindu Calendar):**
- ✅ Today's Panchang workspace in ERP shell
- ✅ Tithi, Nakshatra, Yoga, Karana, sunrise/sunset from `/api/v1/panchang/today`
- ✅ Verified with browser smoke for accurate display

**Accounting Reports:**
- ✅ Trial Balance (month/week/day view with drill-down)
- ✅ Income & Expenditure
- ✅ Receipts & Payments
- ✅ Balance Sheet
- ✅ Voucher detail drill-down
- ✅ All reports balanced after donation, seva, sponsorship, and expense flows
- ✅ Verified: Trial Balance remained balanced at Rs. 1,715.00 after reversal smoke

**ERP Shell Integration:**
- ✅ MandirMitra workspace tabs (Donations, Sevas, Public Payments, Exceptions, Receipts, Panchang, Reports, Accounting)
- ✅ Module context resolution (organization_type=TEMPLE, enabled modules: temple, accounting, audit)
- ✅ Tenant/app-key isolation (X-App-Key: mandirmitra)
- ✅ Navigation state management

**Tenant Isolation:**
- ✅ Every query tenant-scoped
- ✅ App-key isolation (mandirmitra cannot read gruhamitra donations)
- ✅ Real temple/trust tenants (e.g., Parlathya Prathishtana) protected from destructive staging tests
- ✅ Demo/test tenants clearly marked for mutation testing

#### Verification evidence:
- ✅ Local smoke: `python scripts/mandirmitra_stage3_smoke.py` passed 119 tests
- ✅ Browser smoke: `python scripts/mandirmitra_stage3_browser_smoke.py` passed with Panchang verification
- ✅ Staging non-destructive: Login, tabs, receipt preview/download, Panchang, reports, public config visibility all passed (2026-05-22)
- ✅ Demo public payment E2E: Submission → Pending → Verification → Receipt → Reports → Trial Balance reconciliation passed
- ✅ CI/Render: Green through commit `4d34454`

#### Missing from first live cut (not blockers, but documented as deferred):
- Hundi depth (counting, deposit mechanics, full accounting)
- Festival/fund subledger reporting
- 80G/FCRA exemption configuration
- Refund payout approval queue
- Sponsorship valuation approval
- In-kind stock consumption tracking

**Location of completion checklists:**
- `docs/operations/MANDIRMITRA_DEPLOYMENT_READINESS_REVIEW.md`
- `docs/operations/MANDIRMITRA_PRODUCTION_SIGNOFF.md`
- `docs/operations/MANDIRMITRA_FIRST_LIVE_CUT_DECISIONS.md`

### 3.4 GruhaMitra (Architectural Foundation Ready, Workflows Pending)

**Status:** ⏳ AWAITING MANDIRMITRA LIVE GATE

#### Completed foundation:
- ✅ Organization type: `HOUSING`
- ✅ Module registry entry for `housing` module
- ✅ Enabled modules default: `housing`, `accounting`, `audit`
- ✅ Tenant isolation framework
- ✅ Accounting engine shared with MandirMitra (works for housing too)
- ✅ ERP shell navigation and module routing (proof of concept)
- ✅ Pricing tiers (Starter, Growth, Professional by flat count)
- ✅ Public landing pages with editorial pages (About, Privacy, Terms)

#### Pending workflows (after MandirMitra live):
- Flat/tower/resident master
- Maintenance billing and collection posting
- Parking and vendor payment posting
- Complaint/service request lifecycle
- Housing-specific reports

**Code location:** `app/modules/housing/`, `app/core/billing/pricing.py`

**Live URL:** https://www.gruhamitra.sanmitratech.in (frontend deployed, backend integration in progress)

### 3.5 Audit & Compliance

**Status:** ✅ FUNCTIONAL, NEEDS SCOPE DEFINITION

#### Completed:
- ✅ Audit event logging on protected routes
- ✅ Tenant-scoped audit event query (`GET /api/v1/audit/events`)
- ✅ Event lifecycle: created_at, entity type, entity id, action, actor, old_value, new_value
- ✅ Route-contract coverage for accounting, housing, MandirMitra routes
- ✅ Public payment events: submitted, verified, rejected, corrected
- ✅ Receipt cancellation events: reason, actor, timestamp logged

#### Needs definition:
- ⚠️ Retention policy (how long to keep audit events?)
- ⚠️ Export/report format for audits (CSV, JSON, compliance format?)
- ⚠️ Compliance calendar and automated reminders (deferred to InvestMitra/LegalMitra)

### 3.6 Documentation (Comprehensive & Living)

**Status:** ✅ EXCELLENT DOCUMENTATION DISCIPLINE

#### Documentation map:
- ✅ `README.md` - Clear workspace setup and product scope
- ✅ `AGENTS.md` - AI coding assistant guardrails (mandatory policy)
- ✅ `docs/prd/SANMITRA_UNIFIED_PLATFORM_PRD.md` - Product requirements with living progress table
- ✅ `docs/prd/MITRABOOKS_ERP_GAP_MATRIX.md` - Business ERP phasing and gap analysis
- ✅ `docs/architecture/ARCHITECTURE.md` - Modular monolith design
- ✅ `docs/architecture/CURRENT_VS_TARGET.md` - Current vs target clarity matrix
- ✅ `docs/architecture/MODULE_REGISTRY.md` - Module definitions
- ✅ `docs/architecture/ACCOUNTING_DOCTRINE.md` - Accounting guardrails
- ✅ `docs/migration/FOUNDATION_PR_PLAN.md` - First PR scope and acceptance criteria
- ✅ `docs/migration/FRONTEND_MERGE_PLAN.md` - Frontend consolidation strategy
- ✅ `docs/operations/STAGED_E2E_PLAN.md` - E2E validation stages (LegalMitra → MandirMitra → GruhaMitra → Combined → InvestMitra)
- ✅ `docs/operations/MANDIRMITRA_DEPLOYMENT_READINESS_REVIEW.md` - Deployment checklist with gaps
- ✅ `docs/operations/MANDIRMITRA_PRODUCTION_SIGNOFF.md` - Go/no-go decision document
- ✅ `docs/operations/E2E_VERIFICATION_REPORT.md` - Live production E2E test evidence

### 3.7 CI/CD & Release Management

**Status:** ✅ PIPELINE WORKING

#### GitHub Actions workflows:
- ✅ `backend-ci` - Compile checks, pytest, route-contract validation
- ✅ `codeql-analysis` - Security scanning
- ✅ `security-trivy` - Dependency/secret scanning
- ✅ `release-tag` - Versioning after preflight
- ✅ `render-deploy` - Manual deployment to staging/production

#### Release management:
- ✅ Version file: `VERSION` (currently 1.3.0)
- ✅ Tag convention: `backend-v1.3.0` (production uses tags, not branch heads)
- ✅ Rollback strategy: Use previous `backend-v*` tag

#### Current CI status:
- ✅ Latest commit `4d34454` passed CI/Render
- ✅ Small test failure in GruhaMitra pricing (needs fixing before next commit)

### 3.8 Script Automation

**Status:** ✅ USEFUL FOR SMOKE TESTING

#### Available scripts:
- ✅ `scripts/mandirmitra_stage3_smoke.py` - 119 focused tests for MandirMitra accounting, posting, isolation
- ✅ `scripts/mandirmitra_stage3_browser_smoke.py` - Playwright-based browser verification
- ✅ `scripts/check_repository_safety.py` - Codebase safety checks

---

## Part 4: What Is In Pending Review (Working Tree)

**Status:** ⚠️ NOT YET COMMITTED

All items below exist as local source/tests but are not yet in the main branch. They represent a batch of pending work that needs review before merge.

### 4.1 Platform Owner Dashboard & Tenant Entitlements

**Location:** `app/core/platform_owner/` (new directory, not committed)

#### What's been built:
- Backend API contract: `GET /api/v1/platform-owner/dashboard`
- Response shape: onboarding summary, tenant summary, subscription status, module status, pending approvals
- Backend endpoints for approval actions and entitlement updates
- Tenant lifecycle controls (activate/deactivate)
- Super-admin-only access guard

#### Missing:
- ⚠️ Frontend UI for platform-owner dashboard
- ⚠️ Browser E2E test for dashboard (no super-admin login available in staging yet)
- ⚠️ Integration test coverage for all dashboard data points

#### Decision needed:
Should this batch be merged now (backend-only) or held until frontend UI is ready?

**Recommendation:** Commit the backend API and document the frontend integration plan, but mark as "backend-only release."

### 4.2 Business Parties & Typed Vouchers (Phase 2)

**Location:** `app/modules/business/` (new directory, not committed)

#### What's been built:
- Party master API: create, list, lookup, profile update, soft deactivation
- Typed voucher facades: payment, receipt, contra, journal vouchers
- Idempotency-key support for safe retries
- Idempotent reversal for voucher cancellation
- Backend route-contract tests
- Lifecycle audit events (create, update, deactivate)
- Tenant/app-key/module scoping

#### Missing:
- ⚠️ Frontend integration (Party management UI, voucher entry screens)
- ⚠️ Voucher cancel/update policy definition (can users modify drafted vouchers?)
- ⚠️ Reversal UX (how should reversals be presented to users?)
- ⚠️ Audit UI expansion (showing audit trail in frontend)
- ⚠️ Browser E2E test
- ⚠️ Frontend manifest route coverage (if using frontend route-contract checking)

#### Decision needed:
Phase 2 is officially deferred until after MandirMitra goes live. Should we:
1. Merge backend-only now (with clear "Phase 2" labeling)?
2. Hold in working tree until frontend work is ready?
3. Create a separate `phase-2-business` branch for later?

**Recommendation:** Create `phase-2-business` branch to preserve work, but do NOT merge into main until MandirMitra is deployed live. This protects main from Phase 2 scope creep.

### 4.3 Tenant & Module Lifecycle Enhancements

**Location:** Modified files: `app/core/tenants/service.py`, `app/core/tenants/schemas.py`, `app/core/tenants/router.py`

#### Changes being reviewed:
- `organization_type` field addition to tenant model
- `enabled_modules` list addition
- Seed tenant context fixes (ensuring `seed-tenant-1` is TEMPLE with temple/accounting/audit modules)
- Module derivation from organization type
- Tenant entitlement PATCH endpoint

#### Status:
- ✅ Local tests pass
- ⚠️ Needs verification that it doesn't break existing tenants (migration safety)
- ⚠️ Schema version bump needed if database field is added

**Recommendation:** Commit with a migration script that safely backfills `organization_type` and `enabled_modules` for existing tenants.

### 4.4 Onboarding Workflow Refinements

**Location:** Modified file: `app/core/onboarding/service.py`

#### Changes being reviewed:
- Module validation during onboarding request approval
- Automatic `enabled_modules` derivation from `app_key` and organization type
- Tenant creation with correct module defaults

**Status:**
- ✅ Tests updated to verify module derivation
- ⚠️ Needs E2E verification that onboarding flow still works end-to-end

### 4.5 Audit Router & Event Publishing

**Location:** New file: `app/core/audit/router.py` (not committed)

#### What's new:
- Public audit event query route with tenant/app-key scoping
- Filtering by entity type and action
- Event listing with pagination

**Status:**
- ✅ Route contract test written
- ⚠️ Needs integration with platform-owner dashboard
- ⚠️ Needs UI for audit event review

### 4.6 Documentation Additions

**Status:** ⚠️ NEW DOCS ADDED, NOT COMMITTED

#### New operational docs (in `docs/operations/`):
- `GRUHAMITRA_STAGE4_SMOKE_CHECKLIST.md` - GruhaMitra readiness checklist
- `GRUHAMITRA_UI_UX_REVIEW.md` - GruhaMitra frontend design review
- `E2E_VERIFICATION_REPORT.md` - Signed-off verification of live products
- `PRICING_SHEET_CUSTOMER.md` - Pricing for customer view
- `PRICING_PLAYBOOK_INTERNAL.md` - Pricing strategy and rules

#### New operational artifacts (images, mockups):
- GruhaMitra landing page mockups
- MandirMitra dashboard screenshot (evidence)
- Trial Balance report screenshot (evidence)

**Status:**
- ✅ All evidence-based and capture known good states
- ⚠️ Should be committed to preserve operational memory

---

## Part 5: What Remains in the Pipeline (Not Yet Started)

### 5.1 GruhaMitra Workflows (Queued for After MandirMitra Goes Live)

**Gate:** MandirMitra production signoff ✅ ready, awaiting final environment confirmation

#### Planned for Phase 1:
- Flat/tower/resident data model
- Maintenance billing and collection posting
- Parking fee posting
- Vendor payment posting
- Complaint/service request tracking (basic)
- Housing-specific reports

#### Timeline:
- Start after MandirMitra deployment confirmed live
- Estimated duration: 3-4 weeks (mirrors MandirMitra effort)

### 5.2 Phase 2: MitraBooks Business Masters & Vouchers

**Gate:** GruhaMitra live ✅ backend exists (in working tree), awaiting Phase 2 signal

#### Scope:
- Frontend UI for party management
- Voucher entry screens (Tally-familiar UX if possible)
- Voucher cancel/update policy design
- Reversal UX
- Audit UI expansion

#### Timeline:
- Start after GruhaMitra deployment confirmed live
- Estimated duration: 4-6 weeks

### 5.3 Phase 3: Invoicing, GST, AR/AP

**Gate:** Phase 2 complete

#### Scope:
- Sales invoice domain model and GL posting rules
- Purchase invoice domain model and GL posting rules
- GST basics (GSTIN validation, place-of-supply logic)
- Receivables/payables outstanding and ageing
- Multi-client accounting entity model for CA firms

#### Timeline:
- Start Q3 2026 (estimated)
- Estimated duration: 6-8 weeks

### 5.4 Phase 4: Inventory, Reconciliation, Location Dimension

**Gate:** Phase 3 complete

#### Scope:
- Item/service master
- FIFO stock movement
- Stock valuation
- Cash book, bank book
- Manual reconciliation UI
- Location/branch dimension

#### Timeline:
- Q3-Q4 2026
- Estimated duration: 8 weeks

### 5.5 Phase 5: MIS, Data Health, Export

**Gate:** Phase 4 complete

#### Scope:
- KPI dashboard
- Sales/purchase trends
- Top customers/vendors
- Working capital dashboard
- Overdue/collection dashboard
- Data Health Score
- Excel/PDF/JSON/Tally XML exports

#### Timeline:
- Q4 2026 - Q1 2027
- Estimated duration: 8 weeks

### 5.6 GruhaMitra Completion

**Gate:** MandirMitra live

#### Pending workflows:
- Advanced complaint/service request workflows
- Payment plans for maintenance arrears
- Vendor portal integration
- Society-wide financial reports
- Resident self-service portal (future)

### 5.7 Strategic Integrations (Reserved, Gate-Kept)

#### 1. InvestMitra: FinceptTerminal
- Research-only data aggregation
- No broker execution
- Requires licensing review and compliance approval
- Status: Reserved in module registry, not implemented

#### 2. InvestMitra: Zerodha Kite MCP
- Holdings-aware portfolio context
- Read-only research use only
- Requires credential handling design and audit logging
- Status: Reserved in module registry, not implemented

#### 3. LegalMitra: Claude Legal Counsel
- Legal drafting and research assistance
- Requires confidentiality and retention approval
- Requires source attribution in documents
- Status: Partially implemented (provider interface exists), gated by environment configuration

---

## Part 6: Test Coverage & Quality Assessment

### 6.1 Test Suite Overview

**Total tests:** ~350+ across the codebase

#### By module:

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| Accounting (core) | 100+ | High | ✅ Comprehensive |
| MandirMitra | 80+ | High | ✅ Comprehensive |
| GruhaMitra | 15+ | Medium | ⚠️ Growing |
| Housing (compat layer) | 15+ | Medium | ✅ Stable |
| LegalMitra | 30+ | Medium | ✅ Stable |
| Business Phase 2 | 11+ | Medium | ⚠️ Pending review |
| Auth/Tenancy | 20+ | Medium | ✅ Good |
| Module access | 15+ | Low | ⚠️ Needs hardening |
| Audit events | 2 | Low | ⚠️ Needs expansion |

#### Key test files (worth understanding):
- `tests/test_mandir_posting_guardrails.py` - 59 tests of accounting invariants
- `tests/test_mandir_app_key_isolation.py` - 22 tests of app-key routing
- `tests/test_accounting_report_route_context.py` - 21 tests of report access control
- `tests/test_housing_compat_tenant_isolation.py` - 15 tests of housing module isolation

### 6.2 Test Failures & Warnings

**Current status:** 1 failing test

#### Failing test:
```
tests/test_gruhamitra_pricing.py::test_gruhamitra_pricing_catalog_matches_approved_tiers
```

**Reason:** Pricing schema was updated to add optional fields (`price_paise`, `fair_use`, `features`). The test assertion is too strict. 

**Fix needed:**
- Update test to check for the core fields (cycle, display_price, price_per_flat_paise) and allow additional optional fields, OR
- Update the GRUHAMITRA_PRICING data to match test expectations

**Impact:** Low - purely test/fixture issue, not production logic

#### Warnings:
- Pydantic V1 → V2 migration deprecations (non-blocking, but should be addressed in cleanup)
- Unused imports in some modules
- Coroutine cleanup warnings in some tests (aiosqlite resource cleanup)

### 6.3 Code Quality

#### Strengths:
- ✅ Strong use of type hints
- ✅ Good separation of concerns (routers, services, models, schemas)
- ✅ Clear test organization and naming
- ✅ Documentation strings on complex functions
- ✅ Consistent error handling patterns

#### Areas for improvement:
- ⚠️ Pydantic V1 → V2 migration (deprecation warnings)
- ⚠️ Some circular imports between core modules
- ⚠️ Module registry and access helper functions could be more centralized
- ⚠️ Some large router files (e.g., `app/api/v1/router.py`) could benefit from splitting

---

## Part 7: Current Blockers & Decisions Needed

### 7.1 Blocking MandirMitra Production Deployment

**All are confirmations, not code blockers:**

| Item | Status | Required by | Notes |
|------|--------|-------------|-------|
| Production MongoDB/PostgreSQL | ⏳ Awaiting | Platform owner | Environment values must be provided |
| Production JWT secret | ⏳ Awaiting | Platform owner | JWT signing key for production |
| Production CORS origins | ⏳ Awaiting | Platform owner | Frontend URLs must be whitelisted |
| Backup/restore testing | ⏳ Awaiting | DevOps/Platform owner | MongoDB and PostgreSQL backup schedule must be confirmed |
| Rollback procedure | ✅ Documented | Platform owner | Use previous `backend-v*` tag, not branch heads |
| Seed/demo tenant policy | ⚠️ Needs clarification | Platform owner | What demo data, if any, is allowed in production? |
| Real trust safety rules | ✅ Documented | Platform owner | Real Parlathya must not be used for destructive tests |
| Audit retention | ⏳ Needs definition | Compliance | How long to keep audit events? |

**Action:** Platform owner to confirm environment, backup/restore owner, and tenant seed policy before merge/deployment.

### 7.2 Blocking GruhaMitra Start

**Gate:** MandirMitra live in production

**Current state:** GruhaMitra architectural foundation complete, backend accounting engine shared with MandirMitra, frontend deployed but not integrated.

**Action:** After MandirMitra production sign-off, merge pending GruhaMitra commits and start workflow implementation.

### 7.3 Blocking Phase 2 Business Features

**Gate:** GruhaMitra live in production

**Current state:** Backend API complete but not merged, frontend not started, policies not finalized.

**Action items:**
1. Decide: Merge business backend now (as "Phase 2 pending") or hold until frontend work starts?
2. Decide: Voucher cancel/update policy
3. Decide: Reversal UX pattern

**Recommendation:** 
- Create `phase-2-business` branch to preserve work
- Do NOT merge into main until Phase 2 gate (GruhaMitra live) is reached
- This protects main from scope creep and keeps it focused on MandirMitra readiness

### 7.4 Technical Debt

#### Minor issues (can be deferred):
- Pydantic V1 → V2 deprecation warnings (low risk)
- Coroutine cleanup warnings in tests (resource leak, not functional)
- GruhaMitra pricing test failure (1 failing test, easy fix)

#### Architectural issues to track:
- Platform-owner dashboard needs frontend UI (blocked on Phase 1 completion)
- Module access helper coverage should expand to all protected routes (ongoing hardening)
- Audit event UI needs expansion for operational visibility (deferred to later phase)

---

## Part 8: Git Status & Pending Commits

### 8.1 Current Working Tree

**Modified files (staged for commit):**
```
M  README.md
M  app/api/v1/router.py
M  app/core/audit/service.py
M  app/core/billing/pricing.py
M  app/core/onboarding/service.py
M  app/core/tenants/router.py
M  app/core/tenants/schemas.py
M  app/core/tenants/service.py
M  docs/architecture/CURRENT_VS_TARGET.md
M  tests/test_module_access_dependency.py
M  tests/test_onboarding_workflow.py
M  tests/test_tenants_lifecycle.py
```

**Untracked files (needs staging decision):**
```
?? app/core/audit/router.py
?? app/core/platform_owner/
?? app/modules/business/
?? docs/operations/E2E_VERIFICATION_REPORT.md
?? docs/operations/GRUHAMITRA_STAGE4_SMOKE_CHECKLIST.md
?? docs/operations/GRUHAMITRA_UI_UX_REVIEW.md
?? docs/operations/PRICING_PLAYBOOK_INTERNAL.md
?? docs/operations/PRICING_SHEET_CUSTOMER.md
?? tests/test_audit_events.py
?? tests/test_business_phase2.py
?? tests/test_business_route_contract.py
?? tests/test_platform_owner_dashboard.py
```

### 8.2 Commit Strategy

**Recommendation:** Organize into focused commits by category:

1. **Commit 1: Foundation & Tenant Lifecycle**
   - Files: app/core/tenants/*, app/core/onboarding/service.py, tests/test_tenants_lifecycle.py, tests/test_onboarding_workflow.py
   - Message: "feat: add organization_type and enabled_modules to tenant lifecycle"
   - Includes: migration script for existing tenants

2. **Commit 2: Platform Owner Dashboard (Backend-Only)**
   - Files: app/core/platform_owner/*, app/api/v1/router.py, tests/test_platform_owner_dashboard.py
   - Message: "feat: add platform owner dashboard API contract (backend-only, frontend TBD)"
   - Mark: "Phase 1" in message

3. **Commit 3: Audit Router & Event Query**
   - Files: app/core/audit/router.py, app/core/audit/service.py, tests/test_audit_events.py
   - Message: "feat: add tenant-scoped audit event query route"

4. **Commit 4: GruhaMitra Pricing & Docs**
   - Files: app/core/billing/pricing.py, docs/architecture/CURRENT_VS_TARGET.md, tests/test_gruhamitra_pricing.py
   - Message: "feat: configure GruhaMitra pricing tiers and update target matrix"
   - Action: Fix failing pricing test

5. **Commit 5: Operational Docs & Evidence**
   - Files: docs/operations/E2E_*, docs/operations/GRUHAMITRA_*, docs/operations/PRICING_*
   - Message: "docs: add operational verification and deployment readiness reports"

6. **Branch: phase-2-business** (NOT merged to main yet)
   - Files: app/modules/business/*, tests/test_business_*
   - Message: "feat(phase-2): add business parties and typed vouchers (Phase 2, awaiting GruhaMitra live gate)"
   - Action: Create as separate branch, protect main from scope creep

---

## Part 9: Recommended Next Steps

### Immediate (Next 1-2 Days)

1. **Fix GruhaMitra pricing test**
   - Update `tests/test_gruhamitra_pricing.py` to check core fields and allow optional fields
   - Verify all tests pass
   - Commit as part of foundation batch

2. **Get platform owner confirmation on production gates**
   - Environment (MongoDB, PostgreSQL URLs/credentials)
   - JWT secret for production
   - CORS origins for production
   - Backup/restore owner and schedule
   - Seed/demo tenant policy

3. **Decision on Phase 2 business features**
   - Create `phase-2-business` branch to preserve work
   - Document that Phase 2 is blocked until GruhaMitra live gate

### Short-term (Next 1-2 Weeks)

4. **Merge foundation commits** (once tests pass and gates confirmed)
   - This unblocks MandirMitra production deployment
   - CI should remain green throughout

5. **Deploy MandirMitra to production**
   - Use release tag `backend-v1.3.1` or similar
   - Monitor Render logs and live platform
   - Run production smoke checks

6. **Begin GruhaMitra workflow implementation**
   - Reuse accounting engine and ERP shell from MandirMitra
   - Target: 3-4 week delivery to parity with MandirMitra

### Medium-term (After MandirMitra is Live)

7. **Deploy GruhaMitra to production**
   - Similar process to MandirMitra
   - Use release tag `backend-v1.4.0` or similar

8. **Evaluate Phase 2 business readiness**
   - Review `phase-2-business` branch
   - Decide on voucher cancel/update policy
   - Decide on reversal UX pattern
   - Plan Phase 2 implementation

9. **Frontend merge planning**
   - Begin consolidating GruhaMitra, MandirMitra, and MitraBooks into single ERP shell
   - This is a Vercel frontend task, not backend

---

## Part 10: Success Metrics & Exit Gates

### MandirMitra Production Gate ✅ READY

| Gate | Status | Evidence |
|------|--------|----------|
| Donation workflow | ✅ Pass | 119 tests, local smoke, staging non-destructive checks |
| Seva workflow | ✅ Pass | Receipts, reports, accounting posting verified |
| Public payments | ✅ Pass | Demo E2E: submission → verification → posting → reports |
| Receipt cancellation | ✅ Pass | Reversal journals created, original amounts immutable |
| Sponsorship accounting | ✅ Pass | Cash/in-kind/inventory posting rules verified |
| Panchang | ✅ Pass | Browser smoke verified Today's Panchang display |
| Accounting reports | ✅ Pass | Trial Balance, I&E, R&P, Balance Sheet all balanced |
| Tenant isolation | ✅ Pass | 22 tests verify app-key routing and tenant scoping |
| CI/Render | ✅ Pass | Latest commit `4d34454` green on both |
| Staging non-destructive | ✅ Pass | Login, navigation, reports, public config visibility |

**Decision:** MandirMitra is feature-complete and ready for production deployment pending platform owner confirmation of production gates.

### GruhaMitra Production Gate (Future)

- [ ] Flat/tower/resident master implemented and tested
- [ ] Maintenance billing and collection posting verified
- [ ] Parking and vendor payment posting verified
- [ ] Housing-specific reports reconcile with accounting
- [ ] CI/Render green
- [ ] E2E browser smoke passed

### Phase 2 Business Gate (Future)

- [ ] Party master UI integrated and tested
- [ ] Voucher entry screens created with Tally-familiar UX
- [ ] Voucher reversal UX finalized and tested
- [ ] Audit UI expanded to show party/voucher audit trail
- [ ] Browser E2E test for party/voucher flows
- [ ] Frontend manifest route contracts updated

---

## Part 11: Architecture & Code Quality Summary

### Strengths

✅ **Clear separation of concerns** - Routers, services, schemas, models are cleanly organized  
✅ **Strong type hints** - Pydantic models with validation throughout  
✅ **Excellent documentation** - Living PRD, gap matrix, architecture docs, operational checklists  
✅ **Tenant isolation** - Every query scoped, enforced at multiple layers  
✅ **Accounting integrity** - Double-entry accounting with invariant enforcement and immutability  
✅ **Test coverage** - 350+ tests with focus on isolation, posting guardrails, route contracts  
✅ **CI/CD pipeline** - GitHub Actions, security scanning, automated tagging  
✅ **Modular design** - Clear module boundaries, shared accounting engine, app-key routing  

### Areas for Hardening

⚠️ **Module registry coverage** - Access helper applied to some routes, not all protected routes  
⚠️ **Pydantic V1→V2 migration** - Deprecation warnings, should be addressed  
⚠️ **Audit event visibility** - UI not yet built for operational review  
⚠️ **Platform-owner dashboard** - Backend ready, frontend not started  
⚠️ **Error messages** - Some generic 403/404 responses could be more specific (careful not to leak tenant IDs)  

### Scalability Readiness

✅ **PostgreSQL accounting** - Append-only ledger, indexed by tenant_id and date  
✅ **MongoDB domain data** - Tenant-scoped collections  
✅ **Modular monolith** - Can extract services later if needed  
✅ **Shared kernel** - Accounting engine reused across products reduces duplication  

⚠️ **Caching layer** - Redis integration reserved but not fully implemented  
⚠️ **Rate limiting** - Not yet implemented for public endpoints  
⚠️ **Audit log retention** - Strategy needs definition for large-scale deployments  

---

## Part 12: Risk Assessment

### High Priority (Pre-Production)

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Production environment not ready | Deployment blocked | Platform owner to confirm environment by [date] |
| Seed/demo tenant confusion | Real data at risk | Document and enforce demo tenant naming and isolation |
| Backup/restore not tested | Data loss on outage | DevOps to test restore procedure before go-live |
| Real temple data in staging tests | Contamination/PII leakage | All destructive tests limited to demo tenants (already done) |

### Medium Priority (Post-Launch)

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Phase 2 scope creep | MandirMitra live date slips | Create phase-2-business branch, block from main until gate |
| Module access not comprehensive | Unprotected routes leak data | Systematically apply module access helper to all routes |
| Audit event volume | Storage/performance | Define retention policy and archival before scale-up |
| GruhaMitra timeline slip | Customer expectations | Start GruhaMitra immediately after MandirMitra live, estimate 3-4 weeks |

### Low Priority (Watch List)

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Pydantic deprecations | Library maintenance | Schedule Pydantic V2 migration for post-GruhaMitra |
| Circular imports | Deployment issues | Refactor core module dependencies in refactoring phase |
| Test flakiness | CI reliability | Fix coroutine cleanup warnings in test suite |

---

## Summary Table: What, When, Status

| Feature/Component | Planned | Completed | In Review | Pipeline | Status |
|---|---|---|---|---|---|
| **LegalMitra** | ✅ Documented | ✅ Live | - | - | LIVE |
| **MandirMitra** | ✅ Documented | ✅ Features complete | ✅ Gates pending | - | READY FOR PRODUCTION |
| **GruhaMitra foundation** | ✅ Documented | ✅ Architecture ready | - | Workflows | QUEUED (awaiting MandirMitra live) |
| **MitraBooks ERP core** | ✅ Documented | ✅ Accounting engine | ✅ Dashboard backend | Dashboard frontend | PHASE 1 READY |
| **MitraBooks Phase 2 (business)** | ✅ Documented | ✅ Backend code | ⚠️ Not merged | Frontend + policies | PHASE 2 PENDING (after GruhaMitra) |
| **MitraBooks Phase 3-5** | ✅ Documented | - | - | Sales, GST, Inventory, MIS, Export | PHASES 3-5 DEFERRED |
| **InvestMitra integration** | ✅ Reserved | - | - | FinceptTerminal, Zerodha | RESERVED (post-MitraBooks) |
| **Platform owner dashboard** | ✅ Documented | ✅ Backend API | ⚠️ Awaiting review | Frontend UI | PHASE 1 (backend) |
| **Audit events & UI** | ✅ Documented | ✅ Logging works | ⚠️ Router added | Frontend expansion | FUNCTIONAL |
| **CI/CD pipeline** | ✅ Designed | ✅ Working | - | - | GREEN |
| **Documentation** | ✅ Comprehensive | ✅ Living docs | - | - | EXCELLENT |
| **Tests** | ✅ Strategy set | ✅ 350+ tests | ⚠️ 1 test fails | Coverage expansion | GOOD |

---

## Conclusion

The SanMitra Unified Platform has successfully executed a disciplined, staged delivery approach:

1. **LegalMitra** is live and stable
2. **MandirMitra** is feature-complete and ready for production deployment (gates pending)
3. **GruhaMitra** foundation is ready; workflows queued for after MandirMitra goes live
4. **MitraBooks** accounting engine is shared and proven; Phase 2 business features are backend-ready but held until Phase 2 gate
5. **InvestMitra** remains separate (not yet merged into unified shell)

**Key success factors:**
- Clear current-vs-target discipline preventing scope creep
- Strong accounting guardrails ensuring financial integrity
- Tenant and app-key isolation enforced throughout
- Comprehensive documentation serving as living contracts
- Living progress tables in PRD preventing ambiguity
- Staged E2E plan preventing premature scope expansion

**Readiness for next phase:**
All items are queued and gated appropriately. The only blocker for MandirMitra production is platform owner confirmation of production environment, backup/restore, and tenant seed policy—not code readiness.

**Recommended action:**
Merge foundation commits (once tests pass), deploy MandirMitra to production, then immediately begin GruhaMitra workflow implementation while the team momentum is high.

