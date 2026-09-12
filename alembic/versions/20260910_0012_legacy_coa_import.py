"""legacy COA import: Tally/Zoho/CSV source systems + decision audit

Revision ID: 20260910_0012
Revises: 20260623_0011
Create Date: 2026-09-10

Purpose: allow Tally/Zoho/CSV as COA source systems and store append-only
user-confirmed map-or-create decisions (legacy code kept as a searchable alias).
Affected tables: coa_source_accounts (CHECK widened), coa_mapping_decisions (new).
Tenant impact: additive; existing mappings unchanged.
Backfill: none required.
Rollback: drop coa_mapping_decisions; restore the previous source_system CHECK.
Destructive risk: no (CHECK is widened; new table only).
Validation: tests/test_legacy_coa_import.py and accounting route-context tests.
"""

from alembic import op


revision = "20260910_0012"
down_revision = "20260623_0011"
branch_labels = None
depends_on = None


_SOURCE_SYSTEMS = (
    "'ghar_mitra','mandir_mitra','mitra_books','legal_mitra','invest_mitra',"
    "'tally','zoho','csv'"
)


def upgrade() -> None:
    op.execute(
        f"""
        ALTER TABLE coa_source_accounts DROP CONSTRAINT IF EXISTS ck_coa_source_accounts_system;
        ALTER TABLE coa_source_accounts
            ADD CONSTRAINT ck_coa_source_accounts_system
            CHECK (source_system IN ({_SOURCE_SYSTEMS}));
        """
    )
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS coa_mapping_decisions (
            id SERIAL PRIMARY KEY,
            app_key VARCHAR(50) NOT NULL DEFAULT 'mandirmitra',
            tenant_id VARCHAR(64) NOT NULL,
            accounting_entity_id VARCHAR(100) NOT NULL DEFAULT 'primary',
            source_system VARCHAR(30) NOT NULL,
            source_account_code VARCHAR(50) NOT NULL,
            source_account_name VARCHAR(200) NOT NULL,
            action VARCHAR(40) NOT NULL,
            canonical_account_id INTEGER NOT NULL REFERENCES accounts(id),
            canonical_account_code VARCHAR(30),
            canonical_account_name VARCHAR(200) NOT NULL,
            created_account BOOLEAN NOT NULL DEFAULT false,
            suggested_account_id INTEGER,
            suggested_account_name VARCHAR(200),
            suggestion_confidence NUMERIC(5, 2),
            suggestion_reason VARCHAR(40),
            notes TEXT,
            decided_by VARCHAR(120),
            decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            mapping_id INTEGER NOT NULL REFERENCES coa_mappings(id) ON DELETE CASCADE,
            audit_event_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_coa_mapping_decisions_system
                CHECK (source_system IN ({_SOURCE_SYSTEMS})),
            CONSTRAINT ck_coa_mapping_decisions_action
                CHECK (action IN ('mapped_to_existing','created_then_mapped'))
        );
        CREATE INDEX IF NOT EXISTS ix_coa_mapping_decisions_tenant
            ON coa_mapping_decisions (tenant_id);
        CREATE INDEX IF NOT EXISTS ix_coa_mapping_decisions_app_tenant_entity
            ON coa_mapping_decisions (app_key, tenant_id, accounting_entity_id);
        CREATE INDEX IF NOT EXISTS ix_coa_mapping_decisions_app_tenant_entity_system_code
            ON coa_mapping_decisions (
                app_key, tenant_id, accounting_entity_id, source_system, source_account_code
            );
        CREATE INDEX IF NOT EXISTS ix_coa_mapping_decisions_decided_at
            ON coa_mapping_decisions (tenant_id, decided_at);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_coa_mapping_decisions_decided_at;
        DROP INDEX IF EXISTS ix_coa_mapping_decisions_app_tenant_entity_system_code;
        DROP INDEX IF EXISTS ix_coa_mapping_decisions_app_tenant_entity;
        DROP INDEX IF EXISTS ix_coa_mapping_decisions_tenant;
        DROP TABLE IF EXISTS coa_mapping_decisions;
        """
    )
    op.execute(
        """
        ALTER TABLE coa_source_accounts DROP CONSTRAINT IF EXISTS ck_coa_source_accounts_system;
        ALTER TABLE coa_source_accounts
            ADD CONSTRAINT ck_coa_source_accounts_system
            CHECK (source_system IN (
                'ghar_mitra','mandir_mitra','mitra_books','legal_mitra','invest_mitra'
            ));
        """
    )
