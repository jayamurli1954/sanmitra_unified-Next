# MandirMitra Deployment Readiness Review

Date: 2026-05-22

## Current State

MandirMitra is running inside the MitraBooks ERP shell with tenant/app context, donation receipts, seva receipts, public payment verification, accounting reports, drill-down, and Panchang browser smoke covered locally.

Latest local evidence:

- `node --check frontend\mitrabooks-erp\app.js` passed.
- `python scripts\mandirmitra_stage3_browser_smoke.py` passed and verified the active Panchang workspace.
- `python scripts\mandirmitra_stage3_smoke.py` passed compile checks and 119 focused tests.
- `python -m pytest tests\test_mandir_posting_guardrails.py -q` passed 51 tests.

## Target State

MandirMitra should be live-ready like LegalMitra, while remaining inside the MitraBooks ERP shell for accounting-backed temple operations.

Live-ready means:

- Protected routes resolve tenant, app key, organization type, modules, and role from trusted context.
- Donation and seva collections post through MitraBooks double-entry accounting.
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
| Accounting | Passed locally | Donation, seva, and expense postings reconcile through Trial Balance, I&E, R&P, Balance Sheet, drill-down, and voucher detail. |
| Panchang | Passed locally | ERP shell renders Today Panchang with Tithi/Nakshatra/Yoga/Karana from `/api/v1/panchang/today`. |
| Audit trace | Passed locally | Public payment submitted/verified/corrected/rejected events are covered in local smoke/tests. |
| Browser smoke | Passed locally | Playwright verifies MandirMitra shell, module context, public payment/receipt/report UI, and Panchang workspace. |

## Remaining Gaps Before Live Signoff

| Gap | Required decision/work |
| --- | --- |
| Environment configuration | Confirm staging/production values for MongoDB, PostgreSQL, Redis if used, CORS, public frontend URL, receipt/PDF dependencies, and MandirMitra app key. |
| Seed/demo tenant assumptions | Decide which demo temple data, if any, is allowed in staging/production and ensure production onboarding does not depend on seed-only records. |
| Audit retention | Define retention/export expectations for public payment events, receipt events, correction/rejection history, and platform-owner actions. |
| Backup/restore | Confirm MongoDB and PostgreSQL backup schedule and restore test responsibility before production use. |
| Rollback | Backend rollback must use previous release tag; financial data must not be rolled back by editing ledger rows. Use reversal/adjustment entries for accounting corrections. |
| Hundi/festival/fund workflows | Review legacy-live coverage and decide whether these are required for this live cut or documented as post-live Phase 3 additions. |
| Cancellation/refund | Receipt cancellation and financial reversal behavior need explicit live policy and focused tests before enabling operational cancellation/refund UI. |
| 80G/FCRA configuration | Must remain tenant-configured. Do not default eligibility to true. Confirm whether this is required for the first live MandirMitra cut. |
| Devotee privacy | Confirm role-gated access, PII retention/anonymization policy, and logging rules for devotee phone/email/PAN if PAN is later enabled. |

## Release Recommendation

MandirMitra can move to staging deployment review after the current Panchang/UI smoke commit is pushed and CI is green.

Production live signoff should wait until environment configuration, backup/restore, rollback, seed/demo tenant assumptions, and the required-vs-deferred decision for hundi/fund/cancellation/80G-FCRA are recorded.
