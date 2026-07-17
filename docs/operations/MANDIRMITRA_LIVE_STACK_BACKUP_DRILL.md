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

## Non-negotiable rules

- Restore drills must target an **isolated non-production** database/cluster copy — never overwrite live client data as the drill.
- Do not paste connection strings, passwords, or dumps into git, chat, or evidence JSON.
- Prefer restoring **Mongo + Postgres** to compatible points for financial consistency.
- Posted ledger rows are never edited; use reversal/adjustment only.

---

## Part A — MongoDB Atlas (`Cluster0`)

### Current gap (2026-07-17)

Atlas **Backup** page showed upgrade prompts for daily/continuous backups — backups were **not yet enabled**.

### Enable backups

1. Open [MongoDB Atlas](https://cloud.mongodb.com/) → **Project 0** → **Cluster0**.
2. Left menu → **Backup** (or cluster **…** → Edit configuration / Backup).
3. Choose an affordable plan that enables **daily backups** (or continuous PITR if budget allows).
4. Confirm backup is **Active** and note:
   - Schedule (e.g. daily)
   - Retention days (**must be ≥ 7** for signoff)
5. Wait until at least one successful snapshot exists (may take hours after enablement).

### Isolated restore drill

1. Atlas → **Backup** → select a completed snapshot.
2. **Restore** → restore to a **new cluster** or temporary target (e.g. `Cluster0-restore-drill`), **not** in-place overwrite of `Cluster0`.
3. Confirm restore job **Succeeded**.
4. Optional smoke (read-only against restore target if reachable): list a known demo/test collection count; do not point live Render at the drill cluster.
5. Record ISO timestamps for last successful backup and restore drill.
6. Delete or pause the drill cluster when done (cost control).

### Evidence fields to fill

```text
mongodb_backup.provider = MongoDB Atlas
mongodb_backup.service_name = Cluster0 (Project 0)
mongodb_backup.provider_backup_enabled = true   # only after Active
mongodb_backup.schedule = daily | continuous
mongodb_backup.retention_days = <>=7>
mongodb_backup.last_successful_backup_at = <ISO8601>
mongodb_backup.last_restore_test_at = <ISO8601>
mongodb_backup.last_restore_test_status = passed
mongodb_backup.last_restore_test_target = isolated_nonproduction
mongodb_backup.restore_owner = platform-owner
mongodb_backup.restore_location = Atlas Project 0 / Cluster0-restore-drill (name only)
```

---

## Part B — Render PostgreSQL (`sanmitra-postgres-staging`)

### Current gap (2026-07-17)

Service **Recovery** tab is available. Basic-256mb plans may limit PITR; **logical Export** is the minimum path for a restore drill.

### Confirm backup / export

1. Render → **PostgreSQL** → `sanmitra-postgres-staging` → **Recovery**.
2. Note whether **Point-in-Time Recovery** is available on this plan.
3. Under **Export**, click **Create export** (logical backup).
4. Wait until export status is complete; record time.

### Isolated restore drill

Pick one:

**Option 1 — New Render Postgres (preferred):**

1. Create a temporary Postgres instance (e.g. `sanmitra-postgres-restore-drill`) in the same region.
2. Restore/import from the export into that **new** instance only.
3. Confirm instance Available.
4. Optional: run `SELECT 1` / count journals via temporary connection (do not switch live `POSTGRES_URI`).
5. Delete the drill instance when finished.

**Option 2 — PITR recreate (if plan allows):**

1. Recovery → recreate from backup into a **new** database name/instance.
2. Do **not** replace the live instance until a real disaster and platform-owner approval.

### Evidence fields to fill

```text
postgresql_backup.provider = Render
postgresql_backup.service_name = sanmitra-postgres-staging
postgresql_backup.provider_backup_enabled = true   # after export/PITR confirmed
postgresql_backup.schedule = daily | on-demand-export
postgresql_backup.retention_days = <>=7 or Render plan retention>
postgresql_backup.last_successful_backup_at = <ISO8601>
postgresql_backup.last_restore_test_at = <ISO8601>
postgresql_backup.last_restore_test_status = passed
postgresql_backup.last_restore_test_target = isolated_nonproduction
postgresql_backup.restore_owner = platform-owner
postgresql_backup.restore_location = Render / sanmitra-postgres-restore-drill (name only)
```

---

## Part C — After both drills pass

1. Set `cross_store_restore_strategy_confirmed = true` only if you confirm both stores restore to compatible points.
2. Fill `tmp/mandir-stage3-production-operations.json` with real ISO timestamps (no secrets).
3. Keep Path B notes: formal `ENVIRONMENT=production` still deferred.
4. Continue release tags + clean worktree for machine signoff.

## Operator reply checklist (paste into chat)

```text
Mongo backups enabled: yes/no
Mongo schedule / retention days:
Mongo last backup at (ISO):
Mongo restore drill: passed/failed at (ISO); target name:
Postgres export or PITR: yes/no
Postgres last backup/export at (ISO):
Postgres restore drill: passed/failed at (ISO); target name:
Cross-store strategy confirmed: yes/no
```

Do not include connection strings or credentials.
