# MandirMitra Production Signoff

Date: 2026-05-22

Last gate review: 2026-07-17 (Path B security waiver recorded)

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

These areas completed hosted Stage 3 demo mutation on 2026-07-17. They remain disabled, hidden, or clearly marked not-live for production tenants until production ops evidence and (where noted) tenant legal/compliance approval are confirmed.

| Area | Deferred reason |
| --- | --- |
| Hundi depth | Hosted demo maker-checker, accounting, reporting, and reversal passed on 2026-07-17 for `demo-mandir-tenant`. Production use remains disabled until production ops evidence and tenant policy review. |
| Festival/fund depth | Hosted designated-fund, sponsorship, transfer, opening-balance/as-of, approval, and reversal demo mutations passed on 2026-07-17. Production use remains pending production ops evidence. |
| 80G/FCRA issuance | Readiness controls and masked non-filing reports exist and were exercised default-off on hosted staging. Official certificate/filing use requires tenant legal/compliance approval; features remain default-off. |
| Refund payout queue | Hosted approval, settlement, reporting, and retry-safe demo mutations passed on 2026-07-17. Production payout execution remains pending production ops evidence. |
| Sponsorship and inventory depth | Hosted valuation approval, inventory consumption, accounting, and reversal demo mutations passed on 2026-07-17. Production use remains pending production ops evidence. |
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
| Local MandirMitra Stage 3 smoke | Passed on 2026-07-13 across every discovered `test_mandir*.py` suite plus shared accounting, tenancy, module-access, and platform-owner gates. |
| Demo public payment E2E | Passed |
| Receipt PDF smoke | Passed |
| Accounting reports and drill-down | Passed |
| Final local browser smoke | Baseline passed on 2026-05-22. Hardened runners remove embedded passwords, bind destructive confirmation to the exact API origin and explicit demo tenant, reject platform-owner/tenant/app mismatches, require persisted `platform_can_write=true` demo state and distinct maker/approver actors, disable credential-bearing traces/videos, validate 80G/FCRA and fund/inventory drill-down, and emit sanitized JSON evidence. Credentialed local execution passed on 2026-07-14 for `seed-tenant-1`. |
| Hosted staging credentialed Stage 3 | Passed. Browser smoke PASS on 2026-07-15 and guarded destructive 8/8 PASS on 2026-07-17 against Demo Temple (`tenant_id=demo-mandir-tenant`, temple id 1, `platform_can_write=true`) on staging API `https://sanmitra-unified-next-staging-sg.onrender.com` and MitraBooks ERP `https://www.mitrabooks.sanmitratech.in/mitrabooks-erp/`. Distinct actors: `temple.demo.admin@sanmitratech.in` (approver) and `temple.demo.maker@sanmitratech.in` (maker). Sanitized evidence: `tmp/mandir-stage3-browser-smoke.json`, `tmp/mandir-stage3-destructive-evidence.json`. Track 0: `docs/operations/TRACK0_MANDIR_STAGING_CREDENTIALS_RUNBOOK.md`. |
| CI for latest docs/evidence commit | Confirmed green through `4ea3c52`; confirm again for final signoff commit before production. |
| Render deployment | Confirmed green through `4ea3c52`; confirm again for final signoff commit before production. |
| Production env checklist | Partially confirmed. Live stack uses Render service `sanmitra-unified-next-staging-sg` (`ENVIRONMENT=staging` by Path B waiver), MongoDB Atlas `Cluster0`, Postgres `sanmitra-postgres-staging`, frontends `www.mitrabooks.sanmitratech.in` / `www.mandirmitra.sanmitratech.in`. Secrets + bootstrap/demo/open-registration controls hardened 2026-07-17; formal `ENVIRONMENT=production` deferred. |
| Production access policy | Confirmed. No shared/default production password; no `.local` production admin accounts; platform-owner access must use a real email with activation/reset or one-time bootstrap followed by bootstrap disabled. |
| Backup/restore confirmation | **Mongo paid Atlas backup deferred** (platform owner, 2026-07-17) until client/tenant onboarding justifies cost. Optional free logical-export path documented. Provider-managed or operator-managed export + isolated restore still required to close machine signoff later. See `MANDIRMITRA_LIVE_STACK_BACKUP_DRILL.md`. |
| Rollback tag/process | Pending execution. Policy is confirmed: production deploy should use a `backend-v*` tag, rollback redeploys the previous known-good tag, and financial corrections use reversal/adjustment entries rather than ledger edits. |
| Machine-enforced production signoff | Implemented fail-closed in `scripts/verify_mandirmitra_stage3_signoff.py`. It requires fresh matching browser/destructive demo evidence, confirmed backup/restore and production operations evidence bound to the exact deployed release tag and commit, a clean worktree, and a valid release/rollback tag chain before it runs full and release preflight. The evidence contract is documented in `docs/operations/MANDIRMITRA_PRODUCTION_EVIDENCE_SCHEMA.md`; current external confirmations remain pending. |
| Tenant seed/demo policy | Confirmed. Production must not depend on `seed-tenant-1`; demo/test tenants must be clearly named; real trusts are not used for destructive smoke; 80G/FCRA is not default-on; demo UPI IDs are not used for real tenants. |

## Platform waiver — Path B (2026-07-17)

Platform owner decision: keep `ENVIRONMENT=staging` on the live single-stack Render
service for now. Clients remain on current domains and API.

- Security verifier: secrets and disable-controls PASS; **only** ENVIRONMENT blocks full PASS.
- Evidence: `outputs/production-security-config.json` and
  `docs/operations/PRODUCTION_SECURITY_CONFIG_GATE.md` (Platform waiver section).
- This waiver does **not** invent backup PASS or release-tag PASS.

## Platform waiver — Mongo paid Atlas backup deferred (2026-07-17)

Platform owner decision: do **not** purchase MongoDB Atlas Continuous Cloud Backup /
paid snapshot plans at this time.

- Revisit when onboarding clients/tenants with meaningful live data, or when a budgeted
  backup plan is explicitly authorized.
- Optional later evidence path: free `operator_managed_logical_export` (`mongodump`) with
  isolated restore drill — see `MANDIRMITRA_LIVE_STACK_BACKUP_DRILL.md`.
- Machine Mandir Stage 3 ops signoff remains incomplete on backup evidence until that
  optional path is completed or a further waiver is recorded.

## Recommendation

Hosted MandirMitra Stage 3 credentialed smoke and destructive demo are complete for `demo-mandir-tenant`. MandirMitra remains **ops-incomplete** for machine production signoff: backup/restore evidence, `backend-v*` tags, and clean worktree are still required. Full `verify_production_security_config.py` PASS is deferred under Path B until `ENVIRONMENT=production` (or `prod`) is authorized.

GruhaMitra Stage 4 may start only after backup/restore + release-tag discipline are confirmed, or after an **additional** explicit platform-owner waiver for Stage 4 start.
