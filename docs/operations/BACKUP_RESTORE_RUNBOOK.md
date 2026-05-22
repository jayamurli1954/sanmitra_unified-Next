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
| MongoDB | Provider-managed scheduled backup or snapshot, preferably MongoDB Atlas cloud backup. | 7 days minimum for first live cut; 30 days preferred after production traffic starts. | Platform owner or named production admin. |
| PostgreSQL | Provider-managed scheduled backup or snapshot, preferably daily. | 7 days minimum for first live cut; 30 days preferred after production traffic starts. | Platform owner or named production admin. |

Before go-live, record:

- Provider and project/service name.
- Backup schedule.
- Backup retention.
- Restore owner.
- Where restore actions are performed.
- Last restore drill date, once available.

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
3. Select the latest known-good provider backup before the incident.
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

As of 2026-05-22:

- Backup policy is defined.
- Provider backup setup still needs confirmation in production.
- Restore owner still needs to be named.
- A restore drill is not required before first live cut, but should be scheduled after go-live.
