"""add journal reversal link

Revision ID: 20260527_0008
Revises: 20260527_0007
Create Date: 2026-05-27

Purpose: add nullable reversal linkage to journal headers so reversal
entries can point to the original immutable journal entry.
Affected table: journal_entries.
Tenant impact: additive only; existing tenant rows keep NULL reversal links.
Backfill: none required.
Rollback: drop the reversal lookup index, foreign key, and nullable column.
Destructive risk: no for upgrade; downgrade removes only this additive column.
Validation: compile accounting modules and run focused accounting tests.
"""

from alembic import op


revision = "20260527_0008"
down_revision = "20260527_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE journal_entries
            ADD COLUMN IF NOT EXISTS reversal_of_journal_id INTEGER;

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_journal_entries_reversal_of'
            ) THEN
                ALTER TABLE journal_entries
                    ADD CONSTRAINT fk_journal_entries_reversal_of
                    FOREIGN KEY (reversal_of_journal_id)
                    REFERENCES journal_entries(id);
            END IF;
        END $$;

        CREATE INDEX IF NOT EXISTS ix_journal_entries_reversal_of
            ON journal_entries(
                app_key,
                tenant_id,
                accounting_entity_id,
                reversal_of_journal_id
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_journal_entries_reversal_of;

        ALTER TABLE journal_entries
            DROP CONSTRAINT IF EXISTS fk_journal_entries_reversal_of,
            DROP COLUMN IF EXISTS reversal_of_journal_id;
        """
    )
