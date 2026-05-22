# MandirMitra Production Signoff

Date: 2026-05-22

## Decision

MandirMitra is ready for first-live production signoff after the final production environment, backup/restore, rollback, and tenant seed policy checks are confirmed.

This signoff covers MandirMitra inside the MitraBooks ERP shell. It does not expand the scope to GruhaMitra or broader MitraBooks business ERP workflows.

## Included First-Live Scope

| Area | Status | Evidence |
| --- | --- | --- |
| Tenant/app context | Ready | MandirMitra runs under `organization_type=TEMPLE`, app key `mandirmitra`, and enabled modules `temple`, `accounting`, and `audit`. |
| Donations | Ready | Donation creation, receipt numbering, bilingual receipt generation, receipt preview/download, reports, and accounting posting passed smoke. |
| Sevas | Ready | Seva booking, bilingual receipt generation, devotee label, Kannada receipt sentence, reports, and accounting posting passed smoke/tests. |
| Public payments | Ready on demo path | No-login demo public payment submission, protected staff verification with dummy UTR/reference, receipt generation/download, reports, balanced Trial Balance, and voucher drill-down passed. |
| Receipts | Ready | Donation/seva receipt history, preview/download, Kannada terminology, and donation/seva-specific receipt text passed verification. |
| Receipt cancellation/reversal | Ready for first-live correction | Original receipt remains immutable; cancellation/reversal creates linked reversal journal and stores reason, actor, timestamp, refund mode/reference where provided. |
| Expenses | Ready | MandirMitra quick expense posts through shared accounting and appears in expense/report sections correctly. |
| Sponsorship accounting | Ready at posting level | Cash sponsorship, valued in-kind consumables, inventory-enabled in-kind treatment, and precious article accounting have focused coverage. |
| Panchang | Ready for first live cut | ERP shell renders the Panchang workspace backed by `/api/v1/panchang/today`. Further depth can continue after live cut. |
| Reports | Ready | Receipts, donation, seva, devotee, accounting reports, Trial Balance, I&E, R&P, Balance Sheet, and drill-down are verified. |
| Accounting guardrails | Ready | Donation, seva, expense, sponsorship, public payment verification, and reversals post through the shared double-entry accounting service. Trial Balance balances after smoke flows. |

## Required Production Checks Before Go-Live

| Check | Required confirmation |
| --- | --- |
| GitHub CI | Green for the release commit/tag. |
| Render deployment | Green for staging and selected production target. |
| Environment values | Production MongoDB, PostgreSQL, JWT, CORS origins, public frontend URLs, app key, receipt/PDF dependencies, and optional Redis/job settings are confirmed. |
| Demo/seed policy | Production must not depend on local seed-only data. Demo/test tenants must be clearly marked and never confused with real trusts. |
| Real trust safety | Real temple/trust tenants must not be used for destructive smoke unless explicitly approved by the platform owner and tenant. |
| Backup/restore | MongoDB and PostgreSQL backup schedule and restore owner are confirmed before live financial usage. |
| Rollback | Rollback uses the previous known-good `backend-v*` tag. Financial data must not be rolled back by editing ledger rows; use reversal/adjustment entries. |
| Audit retention | Retention/export expectations for receipt, payment, correction, rejection, reversal, and platform-owner events are confirmed. |
| Support readiness | Admin knows how to verify public payments, download receipts, reverse wrong receipts, and inspect accounting drill-down. |

## Deferred Scope

These areas are not blockers for the first live cut, but must remain disabled, hidden, or clearly marked not-live until their gates are implemented and tested.

| Area | Deferred reason |
| --- | --- |
| Hundi depth | Counting, deposit, receipt/accounting rules, and audit tests are not complete enough for production use. |
| Festival/fund depth | Full event/fund subledger reporting, restricted/corpus fund handling, and fund transfer approvals are not complete. |
| 80G/FCRA issuance | Must be tenant-configured and compliance-reviewed; eligibility must not default to true. |
| Refund payout queue | Basic reversal metadata is ready, but approval queue, payout settlement status, and refund exports are deferred. |
| Sponsorship approval/report depth | Posting is covered; valuation approval, inventory consumption, and event/fund subledger reports remain later work. |
| Advanced exports | Report export packs can follow after first live cut. |
| GruhaMitra | Starts only after MandirMitra first-live signoff is accepted. |

## Tenant Safety Rules

- Public page submission is guarded to demo/test tenants.
- Real public-enabled trusts may be used only for read/config visibility checks unless explicitly approved.
- Staff verification is protected and tenant-scoped.
- `X-Tenant-ID` must not be used as a normal tenant switch. Any super-admin override must be explicit and audited.
- `X-App-Key`, module access, organization type, and role must remain enforced on protected routes.

## Accounting Safety Rules

- No financial workflow may write directly to ledger tables.
- Posted entries are immutable.
- Corrections must use reversal or adjustment journals.
- Trial Balance must remain balanced after donation, seva, expense, sponsorship, public payment verification, and receipt reversal.
- Reports must derive from posted accounting records, not direct balance mutation.

## Go/No-Go Summary

| Gate | Status |
| --- | --- |
| Local MandirMitra Stage 3 smoke | Passed |
| Demo public payment E2E | Passed |
| Receipt PDF smoke | Passed |
| Accounting reports and drill-down | Passed |
| Final local browser smoke | Passed on 2026-05-22 with `python scripts\mandirmitra_stage3_browser_smoke.py --api-base http://127.0.0.1:8001`; context returned `organization_type=TEMPLE` with `accounting`, `audit`, and `temple` modules. |
| CI for latest docs/evidence commit | Confirmed green through `4ea3c52`; confirm again for final signoff commit before production. |
| Render deployment | Confirmed green through `4ea3c52`; confirm again for final signoff commit before production. |
| Production env checklist | Partially confirmed. MongoDB, Mongo DB name, PostgreSQL, JWT, allowed app keys, `mandirmitra` app-key behavior, demo bootstrap off, super-admin bootstrap off, and receipt PDF fallback are confirmed. MitraBooks ERP production frontend URL remains pending. |
| Production access policy | Confirmed. No shared/default production password; no `.local` production admin accounts; platform-owner access must use a real email with activation/reset or one-time bootstrap followed by bootstrap disabled. |
| Backup/restore confirmation | Pending. MongoDB and PostgreSQL backup schedule, retention, storage location, restore owner, and restore process must be confirmed before live financial use. |
| Rollback tag/process | Pending execution. Policy is confirmed: production deploy should use a `backend-v*` tag, rollback redeploys the previous known-good tag, and financial corrections use reversal/adjustment entries rather than ledger edits. |
| Tenant seed/demo policy | Confirmed. Production must not depend on `seed-tenant-1`; demo/test tenants must be clearly named; real trusts are not used for destructive smoke; 80G/FCRA is not default-on; demo UPI IDs are not used for real tenants. |

## Recommendation

MandirMitra is ready for production signoff review, but not yet production-approved. Production approval remains blocked by the pending MitraBooks ERP production frontend URL, backup/restore setup, and release tag/rollback execution.

Do not start GruhaMitra production migration until the pending production checks above are marked confirmed or explicitly waived by the platform owner.
