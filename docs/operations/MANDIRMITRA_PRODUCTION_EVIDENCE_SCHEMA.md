# MandirMitra Production Evidence Contract

## Purpose

This contract defines the sanitized, machine-readable operational evidence required by `scripts/verify_mandirmitra_stage3_signoff.py`. It does not approve production by itself and must not contain credentials, tokens, donor details, payment references, or other tenant data.

## Current State

The Stage 3 automated gate is implemented. Local credentialed demo (2026-07-14) and hosted staging credentialed browser smoke (2026-07-15) plus guarded destructive 8/8 (2026-07-17) on `demo-mandir-tenant` have passed with sanitized evidence under `tmp/`. Provider backup confirmation, production frontend/API verification, and reviewed release/rollback tags remain pending for production signoff.

## Target State

An authorized operator supplies three fresh JSON files stored inside this workspace:

1. Browser evidence emitted by `scripts/mandirmitra_stage3_browser_smoke.py`.
2. Destructive demo evidence emitted by `scripts/run_mandirmitra_stage3_destructive.py --execute` against the same explicit demo tenant and origins.
3. Operations evidence following the schema below.

The verifier then checks evidence freshness and consistency, release cleanliness, release and rollback tags, full local preflight, and production release preflight. Any missing or inconsistent requirement blocks signoff.

## Operations Evidence Schema

Use operational identifiers only. `restore_location` should name a provider vault, project, or documented runbook location; it must not contain a credential or connection string.

```json
{
  "status": "confirmed",
  "confirmed_at": "2026-07-13T12:00:00+00:00",
  "confirmed_by_role": "release-operator-role",
  "production_frontend_origin": "https://erp.example.org",
  "production_api_origin": "https://api.example.org",
  "deployed_release_tag": "backend-v1.3.0",
  "deployed_commit_sha": "0123456789abcdef0123456789abcdef01234567",
  "mongodb_backup": {
    "provider": "provider-name",
    "service_name": "production-mongodb-service",
    "provider_backup_enabled": true,
    "schedule": "daily",
    "retention_days": 14,
    "last_successful_backup_at": "2026-07-13T02:00:00+00:00",
    "last_restore_test_at": "2026-07-01T10:00:00+00:00",
    "last_restore_test_status": "passed",
    "last_restore_test_target": "isolated_nonproduction",
    "restore_owner": "operations-role",
    "restore_location": "provider-project-or-vault-name"
  },
  "postgresql_backup": {
    "provider": "provider-name",
    "service_name": "production-postgresql-service",
    "provider_backup_enabled": true,
    "schedule": "daily",
    "retention_days": 14,
    "last_successful_backup_at": "2026-07-13T02:00:00+00:00",
    "last_restore_test_at": "2026-07-01T10:00:00+00:00",
    "last_restore_test_status": "passed",
    "last_restore_test_target": "isolated_nonproduction",
    "restore_owner": "operations-role",
    "restore_location": "provider-project-or-vault-name"
  },
  "cross_store_restore_strategy_confirmed": true,
  "demo_bootstrap_disabled": true,
  "super_admin_bootstrap_disabled": true,
  "production_health_verified": true,
  "production_frontend_verified": true,
  "cors_verified": true,
  "financial_rollback_policy": "reversal_or_adjustment_only"
}
```

Replace the example release tag and commit SHA with the exact deployed release. The
commit SHA must be the full 40-character commit referenced by the release tag. Restore
tests must have completed successfully against an isolated non-production target; a
restore into production is not acceptable gate evidence.

## Verification Command

```powershell
python scripts\verify_mandirmitra_stage3_signoff.py `
  --browser-evidence tmp\mandir-stage3-browser-smoke.json `
  --destructive-evidence tmp\mandir-stage3-destructive-evidence.json `
  --operations-evidence tmp\mandir-stage3-production-operations.json `
  --rollback-tag backend-v<previous-version>
```

The current `VERSION` determines the required release tag. Both release and rollback tags must exist, be distinct, and form an ancestor chain; the release tag must point at the clean current `HEAD`. Operations evidence must name that exact deployed release tag and its full 40-character commit SHA. The verifier rejects evidence for a different deployment.

Each backup must have succeeded within the previous two days, retain at least seven days of recovery points, and have a successful restore test from the previous 90 days. Restore tests must target an isolated non-production database. A configured backup without a successful isolated restore test is not sufficient production evidence.

## Gap and Implementation Sequence

1. Provision or identify a clearly marked demo/test MandirMitra tenant with two authorized non-platform actors.
2. Run browser and guarded destructive evidence against the same tenant and origins.
3. Obtain backup, restore-owner, production health, frontend, and CORS confirmations from the responsible operator.
4. Review the release commit, create the release and prior known-good rollback tags through the normal release process, and ensure the worktree is clean.
5. Run the verifier. Do not manually reinterpret a blocked result as passed.

## Non-Goals

- This contract does not create tags, deploy services, mutate a real trust tenant, or provision backups.
- It does not store screenshots, secrets, donor PII, PAN values, UTRs, payment references, or access credentials.
- It does not permit financial rollback by editing or deleting posted ledger rows.
