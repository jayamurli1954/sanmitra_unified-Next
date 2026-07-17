# MandirMitra Operations Evidence Template

## Purpose

After **hosted Stage 3 credentialed PASS** (and matching local evidence), an authorized
operator fills `tmp/mandir-stage3-production-operations.json` using the schema in
[`MANDIRMITRA_PRODUCTION_EVIDENCE_SCHEMA.md`](./MANDIRMITRA_PRODUCTION_EVIDENCE_SCHEMA.md).
That file is operational evidence for `scripts/verify_mandirmitra_stage3_signoff.py`. It is
not production approval by itself.

Do not store credentials, tokens, donor PII, payment references, or connection strings.

## Remaining checklist

Hosted Stage 3 credentialed demo is complete. Production signoff still requires the
ops items below; confirm each separately and do not invent a PASS.

| Item | Status | Notes |
| --- | --- | --- |
| Hosted staging credentialed MandirMitra demo (browser + guarded destructive) | PASS (2026-07-15 / 2026-07-17) | Demo Temple `demo-mandir-tenant`; evidence `tmp/mandir-stage3-browser-smoke.json`, `tmp/mandir-stage3-destructive-evidence.json`. Track 0: [`TRACK0_MANDIR_STAGING_CREDENTIALS_RUNBOOK.md`](./TRACK0_MANDIR_STAGING_CREDENTIALS_RUNBOOK.md). |
| MongoDB + PostgreSQL provider backup + isolated restore confirmation | PENDING | Live-stack click path: [`MANDIRMITRA_LIVE_STACK_BACKUP_DRILL.md`](./MANDIRMITRA_LIVE_STACK_BACKUP_DRILL.md). Policy: [`BACKUP_RESTORE_RUNBOOK.md`](./BACKUP_RESTORE_RUNBOOK.md). Atlas backups not yet enabled on Cluster0; Render Postgres Recovery needs export/restore drill. |
| Release tag + prior rollback tag (`backend-v*`) on clean HEAD | PENDING | Exact tag/SHA must match operations evidence. |
| Production security config on Render | HARDENED + Path B waiver (2026-07-17) | Secrets and all disable-controls PASS on `sanmitra-unified-next-staging-sg`. Formal verifier remains BLOCKED only on `ENVIRONMENT=staging` by platform-owner Path B waiver. Evidence: `outputs/production-security-config.json`. See [`PRODUCTION_SECURITY_CONFIG_GATE.md`](./PRODUCTION_SECURITY_CONFIG_GATE.md). |

## Hard rules for the JSON

- `financial_rollback_policy` **must** be exactly `reversal_or_adjustment_only`.
  Never edit or delete posted ledger rows for rollback.
- Backup/restore fields stay placeholders until a real isolated restore drill succeeds.
  A configured backup without a passing restore test is not evidence.
- Replace `REPLACE_*` / example origins with real operational identifiers only when confirmed.

## Placeholder template

Copy to `tmp/mandir-stage3-production-operations.json` and replace every `REPLACE_*` value
when a check is actually confirmed. Leave `status` unset / do not claim `"confirmed"` until
all required fields are real.

```json
{
  "status": "REPLACE_WITH_confirmed_ONLY_WHEN_READY",
  "confirmed_at": "REPLACE_ISO8601_TIMESTAMP",
  "confirmed_by_role": "REPLACE_OPERATOR_ROLE",
  "production_frontend_origin": "https://REPLACE-erp.example.org",
  "production_api_origin": "https://REPLACE-api.example.org",
  "deployed_release_tag": "backend-vREPLACE_MAJOR.MINOR.PATCH",
  "deployed_commit_sha": "REPLACE_FULL_40_CHAR_COMMIT_SHA_FROM_RELEASE_TAG",
  "mongodb_backup": {
    "provider": "REPLACE_PROVIDER_NAME",
    "service_name": "REPLACE_MONGODB_SERVICE_NAME",
    "provider_backup_enabled": false,
    "schedule": "REPLACE_SCHEDULE_e.g._daily",
    "retention_days": 0,
    "last_successful_backup_at": "REPLACE_ISO8601_OR_LEAVE_UNTIL_CONFIRMED",
    "last_restore_test_at": "REPLACE_ISO8601_OR_LEAVE_UNTIL_CONFIRMED",
    "last_restore_test_status": "PENDING",
    "last_restore_test_target": "isolated_nonproduction",
    "restore_owner": "REPLACE_RESTORE_OWNER_ROLE",
    "restore_location": "REPLACE_PROVIDER_PROJECT_OR_VAULT_NAME_NOT_A_CONNECTION_STRING"
  },
  "postgresql_backup": {
    "provider": "REPLACE_PROVIDER_NAME",
    "service_name": "REPLACE_POSTGRESQL_SERVICE_NAME",
    "provider_backup_enabled": false,
    "schedule": "REPLACE_SCHEDULE_e.g._daily",
    "retention_days": 0,
    "last_successful_backup_at": "REPLACE_ISO8601_OR_LEAVE_UNTIL_CONFIRMED",
    "last_restore_test_at": "REPLACE_ISO8601_OR_LEAVE_UNTIL_CONFIRMED",
    "last_restore_test_status": "PENDING",
    "last_restore_test_target": "isolated_nonproduction",
    "restore_owner": "REPLACE_RESTORE_OWNER_ROLE",
    "restore_location": "REPLACE_PROVIDER_PROJECT_OR_VAULT_NAME_NOT_A_CONNECTION_STRING"
  },
  "cross_store_restore_strategy_confirmed": false,
  "demo_bootstrap_disabled": false,
  "super_admin_bootstrap_disabled": false,
  "production_health_verified": false,
  "production_frontend_verified": false,
  "cors_verified": false,
  "financial_rollback_policy": "reversal_or_adjustment_only"
}
```

## Verifier (after real evidence exists)

```powershell
python scripts\verify_mandirmitra_stage3_signoff.py `
  --browser-evidence tmp\mandir-stage3-browser-smoke.json `
  --destructive-evidence tmp\mandir-stage3-destructive-evidence.json `
  --operations-evidence tmp\mandir-stage3-production-operations.json `
  --rollback-tag backend-v<previous-version>
```

Do not reinterpret a blocked verifier result as passed.
