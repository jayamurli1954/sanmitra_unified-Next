# Backup and Restore Runbook

Date: 2026-05-22

## Purpose

This runbook defines the minimum backup and restore discipline before MandirMitra is approved for live financial use.

## Scope

This applies to SanMitra unified backend production data:

- MongoDB: tenants, users, module/domain records, devotees, receipts, public payments, audit records, and platform configuration.
- PostgreSQL: accounts, journals, journal lines, ledgers, and accounting reports source data.

Redis/cache data is not a source of truth and is not part of disaster recovery unless a later workflow introduces durable queue ownership.

## Production Backup Requirement

| Store | Required setup | Minimum retention | Owner |
| --- | --- | --- | --- |
| MongoDB | Provider-managed scheduled backup/snapshot **or** operator-managed logical export (`mongodump`) with private encrypted storage outside the repository. Paid Atlas continuous backup may be deferred by platform-owner decision until live data volume justifies cost. | 7 days minimum for first live cut; 30 days preferred after production traffic starts. | Platform owner or named production admin. |
| PostgreSQL | Provider-managed scheduled backup/snapshot **or** Render logical export / PITR when available. | 7 days minimum for first live cut; 30 days preferred after production traffic starts. | Platform owner or named production admin. |

Before go-live, record:

- Provider and project/service name.
- Backup schedule.
- Backup retention.
- Restore owner.
- Where restore actions are performed.
- Last successful restore drill date and result.
- The isolated non-production target used for the restore drill.

## Restore Policy

Restore is for disaster recovery only, such as accidental full database loss, provider failure, or unrecoverable corruption.

Restore must not be used to undo individual temple/accounting mistakes.

Operational mistakes must be corrected by:

- Receipt cancellation/reversal.
- Adjustment journal.
- Corrected replacement receipt where business policy requires it.

Posted accounting rows must not be edited or deleted manually during restore, rollback, or support operations.

## Restore Flow

1. Pause production writes if the incident affects financial data, receipt generation, tenant access, or public payments.
2. Identify impacted store: MongoDB, PostgreSQL, or both.
3. Select the latest known-good provider backup or operator-managed logical export before the incident.
4. Restore into a temporary database when possible and inspect tenant/accounting consistency before replacing production.
5. Restore production only after the platform owner approves the selected backup point.
6. Restart backend services with the restored database connection if required.
7. Run post-restore smoke:
   - Health check.
   - Login/module context.
   - MandirMitra receipts list.
   - Trial Balance balance check.
   - Voucher drill-down.
8. Record the incident, restore point, restore owner, and validation result.

## Cross-Store Caution

MandirMitra workflows can write MongoDB domain records and PostgreSQL accounting entries. If only one store is restored, cross-store records may no longer match.

For financial incidents, prefer restoring both stores to compatible restore points unless the impact analysis proves one-store restore is safe.

## First-Live Status

As of 2026-07-17:

- Backup policy is defined.
- Live single-stack inventory and click-path drills are documented in
  [`MANDIRMITRA_LIVE_STACK_BACKUP_DRILL.md`](./MANDIRMITRA_LIVE_STACK_BACKUP_DRILL.md)
  (Atlas `Cluster0`, Render `sanmitra-postgres-staging`).
- Atlas paid Continuous / cloud backups on Cluster0 are **deferred** by platform-owner decision (2026-07-17) until client/tenant onboarding justifies cost. Optional free operator-managed logical export (`mongodump`) remains available later.
- Render Postgres Recovery/export restore drill into an isolated instance is still optional for machine signoff completeness; preferred mode is `operator_managed_logical_export`.
- Restore owner: platform-owner (named in live-stack drill checklist).
- A successful restore drill for both stores is required for **machine** ops signoff when that gate is closed. Each drill must restore into an isolated non-production target, run the post-restore smoke above, and be no more than 90 days old at signoff.
- `scripts/verify_mandirmitra_stage3_signoff.py` accepts `backup_mode` of `provider_managed_snapshot` or `operator_managed_logical_export`, and still enforces recent backup/export success, minimum retention, successful isolated restore evidence, and the cross-store restore-policy confirmation.
- Path B security waiver does **not** invent backup PASS; Mongo paid Atlas backup is separately deferred.
