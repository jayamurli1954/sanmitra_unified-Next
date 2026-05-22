# MandirMitra Deployment Readiness Review

Date: 2026-05-22

## Current State

MandirMitra is running inside the MitraBooks ERP shell with tenant/app context, donation receipts, seva receipts, public payment verification, accounting reports, drill-down, Panchang browser smoke, and sponsorship accounting coverage locally.

Latest local evidence:

- `node --check frontend\mitrabooks-erp\app.js` passed.
- `python scripts\mandirmitra_stage3_browser_smoke.py` passed and verified the active Panchang workspace.
- `python scripts\mandirmitra_stage3_smoke.py` passed compile checks and 119 focused tests.
- `python -m pytest tests\test_mandir_posting_guardrails.py -q` passed 54 tests.
- GitHub CI was green and the Render workflow deployed green after the latest MandirMitra receipt cancellation/reversal commits.
- Local browser smoke passed against the current backend on `http://127.0.0.1:8001` with `python scripts\mandirmitra_stage3_browser_smoke.py --api-base http://127.0.0.1:8001`.
- Local demo/seed receipt reversal was verified: `DON-0000004` became `reversed`, `REV-112-DON-0000004` appeared in voucher drill-down, Trial Balance stayed balanced at `Rs. 1,715.00`, and I&E, R&P, and Balance Sheet remained consistent.
- Staging non-destructive smoke passed: login/module context, MandirMitra tabs, receipt preview/download, Panchang, reports, balanced accounting reports, and `/mandir-public/` public UPI/config visibility all worked. No destructive test was performed on the visible real trust tenant.
- Startup public-payment bootstrap is now demo-tenant oriented: the real Parlathya trust record is not auto-seeded for public UPI/config, and destructive staging tests require a clearly named demo tenant.
- `/mandir-public/` now supports demo-only public payment submission, creating a pending payment for ERP verification while keeping live trust records visibility-only.

## Target State

MandirMitra should be live-ready like LegalMitra, while remaining inside the MitraBooks ERP shell for accounting-backed temple operations.

Live-ready means:

- Protected routes resolve tenant, app key, organization type, modules, and role from trusted context.
- Donation and seva collections post through MitraBooks double-entry accounting.
- Cash sponsorships and valued in-kind sponsorships post through MitraBooks double-entry accounting.
- Receipts are generated, stable, auditable, and bilingual where required.
- Public devotee payment flow works without login, but staff verification remains protected.
- Panchang is available in the MandirMitra ERP workspace using temple/location settings.
- Reports reconcile with vouchers and drill down to posted accounting detail.

## Deployment Readiness Checklist

| Area | Status | Notes |
| --- | --- | --- |
| Tenant/app context | Passed locally | Browser/API smoke confirms `organization_type=TEMPLE` with `temple`, `accounting`, and `audit` for `mandirmitra`. |
| Donation receipt | Passed locally | Kannada title/terminology and no seva-only note were verified in prior receipt smoke. |
| Seva receipt | Passed locally | Seva title, devotee label, and Kannada received sentence were verified by focused tests and user visual check. |
| Public payments | Passed locally | Temple selector, UPI intent/config, no-login submission, verification, correction, rejection, and audit trace passed. |
| Public payment page visibility | Passed local smoke | ERP Public Payments workspace links to `/mandir-public/`, which loads public-enabled temples and UPI/config/seva/category visibility without requiring login or creating a payment. |
| Accounting | Passed locally | Donation, seva, and expense postings reconcile through Trial Balance, I&E, R&P, Balance Sheet, drill-down, and voucher detail. |
| Sponsorship posting | Passed locally | Cash sponsorship posts to Sponsorship Income; valued in-kind Annadanam posts to expense when inventory is off and inventory when it is on; precious articles classify to temple asset. |
| Sponsorship UI/report fields | Passed syntax/focused tests | ERP quick-entry donation form captures cash/in-kind type, event/festival, item, quantity, and valuation basis; donation reports carry item metadata. |
| Receipt cancellation/reversal | Passed focused tests | Donation and seva receipts can be cancelled from the ERP receipt list; backend posts linked reversal journals and stores reason, actor, timestamp, and refund reference metadata. |
| Panchang | Passed locally | ERP shell renders Today Panchang with Tithi/Nakshatra/Yoga/Karana from `/api/v1/panchang/today`. |
| Audit trace | Passed locally | Public payment submitted/verified/corrected/rejected events are covered in local smoke/tests. |
| Browser smoke | Passed locally | Playwright verifies MandirMitra shell, module context, public payment/receipt/report UI, and Panchang workspace. |
| Staging non-destructive smoke | Passed staging | Login/module context, tabs, receipt preview/download, Panchang, reports, balanced accounting reports, and public no-login visibility were checked without mutating real trust data. |

## Remaining Gaps Before Live Signoff

| Gap | Required decision/work |
| --- | --- |
| Environment configuration | Confirm staging/production values for MongoDB, PostgreSQL, Redis if used, CORS, public frontend URL, receipt/PDF dependencies, and MandirMitra app key. |
| Seed/demo tenant assumptions | Decide which demo temple data, if any, is allowed in staging/production and ensure production onboarding does not depend on seed-only records. |
| Audit retention | Define retention/export expectations for public payment events, receipt events, correction/rejection history, and platform-owner actions. |
| Backup/restore | Confirm MongoDB and PostgreSQL backup schedule and restore test responsibility before production use. |
| Rollback | Backend rollback must use previous release tag; financial data must not be rolled back by editing ledger rows. Use reversal/adjustment entries for accounting corrections. |
| Hundi/festival/fund workflows | Deferred from the first live cut. See `docs/operations/MANDIRMITRA_FIRST_LIVE_CUT_DECISIONS.md`. |
| Sponsorship approval/report depth | Basic UI/report fields are covered, but event/fund subledger reports, in-kind stock consumption for inventory-enabled temples, and valuation approval should be expanded after first live cut. |
| Refund approval/settlement depth | Basic receipt reversal is covered, but a richer approval queue, refund settlement workflow, and refund report exports should be expanded after first live cut. |
| 80G/FCRA configuration | Deferred from the first live cut. Must remain tenant-configured and default-off until registration, receipt text, category/date eligibility, and reports are implemented and tested. |
| Devotee privacy | Confirm role-gated access, PII retention/anonymization policy, and logging rules for devotee phone/email/PAN if PAN is later enabled. |

## Release Recommendation

MandirMitra can move to staging deployment review because the current MandirMitra commits are pushed, CI is green, and Render workflow deployment is green.

Production live signoff should wait until environment configuration, backup/restore, rollback, and seed/demo tenant assumptions are confirmed. Hundi/fund/festival, refund approval/settlement depth, and 80G/FCRA issuance are explicitly deferred from the first live cut.

Staging mutation checks must use a clearly marked demo/test temple tenant. Real temple/trust tenants, including Parlathya Prathishtana, must be limited to non-destructive verification such as login, module context, navigation, report viewing, receipt preview/download, and public no-login configuration checks. As of 2026-05-22, this non-destructive staging smoke has passed. Destructive staging checks require `DEMO_MANDIR_BOOTSTRAP=true`, a staging-only `DEMO_MANDIR_ADMIN_PASSWORD`, and demo public UPI/config values. The public page submission action is demo/test-tenant guarded. The default local ERP demo tenant is `seed-tenant-1`, so pending public payments submitted for `Local ERP Demo Temple` appear under the known local admin login.
