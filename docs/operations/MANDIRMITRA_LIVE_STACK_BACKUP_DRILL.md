# MandirMitra Live-Stack Backup Drill Checklist

Date: 2026-07-17

## Purpose

Operator steps for the **current live single-stack** (Path B: `ENVIRONMENT=staging`).
This does not invent PASS. Fill evidence only after real console actions succeed.

Policy: [`BACKUP_RESTORE_RUNBOOK.md`](./BACKUP_RESTORE_RUNBOOK.md).
Ops template: [`MANDIRMITRA_OPS_EVIDENCE_TEMPLATE.md`](./MANDIRMITRA_OPS_EVIDENCE_TEMPLATE.md).

## Live stack inventory (confirmed)

| Role | Identifier |
| --- | --- |
| API / web service | Render `sanmitra-unified-next-staging-sg` |
| API origin | `https://sanmitra-unified-next-staging-sg.onrender.com` |
| Frontend (ERP) | `https://www.mitrabooks.sanmitratech.in` |
| Frontend (Mandir host) | `https://www.mandirmitra.sanmitratech.in` |
| MongoDB | Atlas Project 0 / cluster **`Cluster0`** |
| PostgreSQL | Render **`sanmitra-postgres-staging`** |
| Security Path B | Hardened controls; `ENVIRONMENT=staging` waived — see `PRODUCTION_SECURITY_CONFIG_GATE.md` |

## Platform decision — Mongo paid backup deferred (2026-07-17)

**Platform owner decision:** Do **not** enable MongoDB Atlas Continuous Cloud Backup / paid
snapshot plans at this time. Cost is not justified for the current early stage.

- Revisit paid Atlas backup when onboarding clients/tenants with meaningful live data,
  or when the platform owner explicitly authorizes a budgeted backup plan.
- Until then, machine Mandir production signoff remains **incomplete** on Mongo backup
  evidence unless an optional free **operator-managed logical export** (`mongodump`)
  path is completed later.
- This waiver covers **paid Atlas provider backup only**. It does not invent a PASS.

## Non-negotiable rules (when any backup path is used)

- Restore drills must target an **isolated non-production** database/cluster copy — never overwrite live client data as the drill.
- Do not paste connection strings, passwords, or dumps into git, chat, or evidence JSON.
- Prefer restoring **Mongo + Postgres** to compatible points for financial consistency.
- Posted ledger rows are never edited; use reversal/adjustment only.
- `backup_mode` must be `provider_managed_snapshot` or `operator_managed_logical_export`.

---

## Part A — MongoDB (`Cluster0`)

### Current status (2026-07-17)

- Atlas paid Continuous / cloud backups: **declined / deferred** (see platform decision above).
- Optional later path: free **operator-managed logical export** (`mongodump` or Atlas Data Export)
  with encrypted private storage **outside** the repository, then restore into an isolated target.

### Path A1 — Paid Atlas snapshots (deferred; do not enable now)

Skip for now. When budget and live data justify it:

1. Atlas → Project 0 → Cluster0 → Backup → enable daily or continuous backups.
2. Retention ≥ 7 days; wait for a successful snapshot.
3. Restore snapshot to a **new** drill cluster (e.g. `Cluster0-restore-drill`).
4. Evidence: `backup_mode=provider_managed_snapshot`, `provider_backup_enabled=true`.

### Path A2 — Operator-managed logical export (optional, $0 Atlas add-on)

Use only when you want Mongo restore evidence without paid Atlas backup:

1. From an authorized machine with Atlas network access, run `mongodump` against Cluster0
   (connection string stays in secret manager / local env only — never in git).
2. Store the dump in a private encrypted location outside this repository; keep ≥ 7 days of exports.
3. Restore into an isolated Mongo target (local Docker Mongo or a temporary free/shared test DB) —
   **never** overwrite Cluster0 as the drill.
4. Record ISO timestamps for export and restore success.

Evidence fields when Path A2 is used:

```text
mongodb_backup.provider = MongoDB tools
mongodb_backup.service_name = Cluster0 (Project 0)
mongodb_backup.backup_mode = operator_managed_logical_export
mongodb_backup.provider_backup_enabled = false
mongodb_backup.schedule = daily mongodump
mongodb_backup.retention_days = >=7
mongodb_backup.last_successful_backup_at = <ISO8601>
mongodb_backup.last_restore_test_at = <ISO8601>
mongodb_backup.last_restore_test_status = passed
mongodb_backup.last_restore_test_target = isolated_nonproduction
mongodb_backup.restore_owner = platform-owner
mongodb_backup.restore_location = vault-or-folder-name / restore-target-name only
```

---

## Part B — Render PostgreSQL (`sanmitra-postgres-staging`)

### Current gap (2026-07-17)

Service **Recovery** tab is available. Basic-256mb plans may limit PITR; **logical Export**
is the preferred low-cost path (`backup_mode=operator_managed_logical_export`).

### Confirm export

1. Render → **PostgreSQL** → `sanmitra-postgres-staging` → **Recovery**.
2. Under **Export**, click **Create export**.
3. Wait until export status is complete; record time.

### Isolated restore drill

1. Create a temporary Postgres instance (e.g. `sanmitra-postgres-restore-drill`) in the same region.
2. Restore/import from the export into that **new** instance only.
3. Confirm instance Available; do not switch live `POSTGRES_URI`.
4. Delete the drill instance when finished.

Evidence fields:

```text
postgresql_backup.provider = Render
postgresql_backup.service_name = sanmitra-postgres-staging
postgresql_backup.backup_mode = operator_managed_logical_export
postgresql_backup.provider_backup_enabled = false
postgresql_backup.schedule = on-demand-export | daily
postgresql_backup.retention_days = >=7 or Render plan retention
postgresql_backup.last_successful_backup_at = <ISO8601>
postgresql_backup.last_restore_test_at = <ISO8601>
postgresql_backup.last_restore_test_status = passed
postgresql_backup.last_restore_test_target = isolated_nonproduction
postgresql_backup.restore_owner = platform-owner
postgresql_backup.restore_location = Render / sanmitra-postgres-restore-drill (name only)
```

---

## Part C — After drills pass (when you choose to complete them)

1. Set `cross_store_restore_strategy_confirmed = true` only if both stores restore to compatible points.
2. Fill `tmp/mandir-stage3-production-operations.json` with real ISO timestamps (no secrets).
3. Keep Path B notes: formal `ENVIRONMENT=production` still deferred.
4. Keep Mongo paid Atlas backup deferred until the onboarding/budget decision.

## Operator reply checklist (paste into chat)

```text
Mongo paid Atlas backup: deferred (platform decision 2026-07-17)
Mongo logical export done: yes/no/skipped
Mongo schedule / retention days:
Mongo last export at (ISO):
Mongo restore drill: passed/failed/skipped at (ISO); target name:
Postgres export done: yes/no/skipped
Postgres last backup/export at (ISO):
Postgres restore drill: passed/failed/skipped at (ISO); target name:
Cross-store strategy confirmed: yes/no/n/a
```

Do not include connection strings or credentials.
