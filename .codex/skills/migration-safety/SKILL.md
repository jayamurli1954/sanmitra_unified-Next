---
name: migration-safety
description: SanMitra database migration, schema, index, seed, and data transformation safety workflow. Use when creating or editing migrations, MongoDB indexes, PostgreSQL schemas, ORM/Pydantic schemas, seeders, backfills, constraints, tenant data transformations, release notes, or rollback plans.
---

# Migration Safety

## Rules

- Prefer additive migrations.
- Never create destructive migrations without explicit user approval.
- Treat these as destructive unless approved: `DROP TABLE`, `DROP COLUMN`, destructive `ALTER COLUMN`, irreversible data rewrite, mass delete/update, truncation, and ledger mutation.
- Adding `NOT NULL` to existing data requires a backfill path first.
- Renames should use a two-phase expand/contract pattern across separate deploys.
- Every tenant-owned table/collection must include tenant scope.
- Add indexes for `tenant_id` plus common lookup fields.
- Use backfill scripts for new required fields on existing data.
- Do not copy secrets, dumps, or live credentials into migrations/seeds.
- Financial data rollback must use reversals/adjustments, not ledger row edits.

## Two-Phase Rename Pattern

Phase 1:

- Add the new column/table.
- Dual-write or backfill from old to new.
- Keep reads compatible with both shapes.

Phase 2:

- Switch reads to the new shape.
- Remove the old shape only after stability and explicit destructive approval.

## Required Migration Note

For every migration or schema-changing PR, document:

- purpose
- affected tables/collections
- tenant impact
- data backfill requirement
- rollback strategy
- destructive risk: yes/no
- approval reference when destructive
- validation command or test coverage

## Large Data And Indexes

- For large PostgreSQL tables, prefer `CREATE INDEX CONCURRENTLY` where the migration framework supports it.
- Run large backfills in batches.
- Document estimated batch size and operational risk.
- Schedule destructive operations during low-traffic windows.

## Accounting And Seed Data

- Accounting table migrations require extra review because financial records are audit-sensitive.
- Adding/removing financial document statuses requires checking every status branch in code.
- Seeders must be idempotent.
- Seeders must not run in production unless explicitly guarded by environment checks.
- Test seed data must use clearly fake values and must not include secrets or real PII.

## Review Checklist

- Confirm migration is non-destructive or explicit approval exists.
- Confirm tenant isolation and indexes are preserved.
- Confirm constraints match current and target behavior.
- Confirm rollback/backfill path is practical.
- Confirm large-table operations avoid unnecessary locks.
- Confirm release/CI validation includes compile/tests or documented exception.
