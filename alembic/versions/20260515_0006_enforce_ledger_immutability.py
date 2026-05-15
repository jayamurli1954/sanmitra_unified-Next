"""enforce posted ledger immutability

Revision ID: 20260515_0006
Revises: 20260427_0005
Create Date: 2026-05-15
"""

from alembic import op


revision = "20260515_0006"
down_revision = "20260427_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_posted_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Posted ledger rows are immutable; create a reversal or adjustment entry instead';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_entries_no_update_delete
        BEFORE UPDATE OR DELETE ON journal_entries
        FOR EACH ROW EXECUTE FUNCTION prevent_posted_ledger_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_journal_lines_no_update_delete
        BEFORE UPDATE OR DELETE ON journal_lines
        FOR EACH ROW EXECUTE FUNCTION prevent_posted_ledger_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_journal_lines_no_update_delete ON journal_lines")
    op.execute("DROP TRIGGER IF EXISTS trg_journal_entries_no_update_delete ON journal_entries")
    op.execute("DROP FUNCTION IF EXISTS prevent_posted_ledger_mutation()")
