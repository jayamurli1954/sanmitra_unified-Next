"""add journal source metadata

Revision ID: 20260527_0007
Revises: 20260515_0006
Create Date: 2026-05-27

Purpose: add nullable source metadata to posted journal headers so
domain modules can retain auditable source document context.
Affected table: journal_entries.
Tenant impact: additive only; existing tenant rows keep NULL source metadata.
Backfill: none required.
Rollback: drop the source lookup index and nullable source columns.
Destructive risk: no for upgrade; downgrade removes only these additive columns.
Validation: compile accounting modules and run focused accounting tests.
"""

from alembic import op


revision = "20260527_0007"
down_revision = "20260515_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE journal_entries
            ADD COLUMN IF NOT EXISTS source_module VARCHAR(50),
            ADD COLUMN IF NOT EXISTS source_document_type VARCHAR(80),
            ADD COLUMN IF NOT EXISTS source_document_id VARCHAR(120);

        CREATE INDEX IF NOT EXISTS ix_journal_entries_source
            ON journal_entries(
                app_key,
                tenant_id,
                accounting_entity_id,
                source_module,
                source_document_type,
                source_document_id
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_journal_entries_source;

        ALTER TABLE journal_entries
            DROP COLUMN IF EXISTS source_document_id,
            DROP COLUMN IF EXISTS source_document_type,
            DROP COLUMN IF EXISTS source_module;
        """
    )
