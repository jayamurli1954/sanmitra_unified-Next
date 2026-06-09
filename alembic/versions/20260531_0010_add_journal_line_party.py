"""add party_id subledger dimension to journal lines

Revision ID: 20260531_0010
Revises: 20260530_0009
Create Date: 2026-05-31

Purpose: add a nullable party_id to posted journal lines so receivable/payable
postings carry a customer/vendor sub-ledger dimension. Enables party-wise
Sundry Debtors / Sundry Creditors reporting that ties to the Trial Balance.
Affected table: journal_lines.
Tenant impact: additive only; existing rows keep NULL party_id (appear as
"Unallocated" in party-wise reports until optionally backfilled).
Backfill: none required for upgrade (optional script bypasses the immutability
trigger to attribute historical rows).
Rollback: drop the party lookup index and the nullable party_id column.
Destructive risk: no for upgrade; downgrade removes only this additive column.
Validation: compile accounting modules and run focused accounting/business tests.
"""

from alembic import op


revision = "20260531_0010"
down_revision = "20260530_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE journal_lines
            ADD COLUMN IF NOT EXISTS party_id VARCHAR(64);

        CREATE INDEX IF NOT EXISTS ix_journal_lines_party
            ON journal_lines(
                app_key,
                tenant_id,
                accounting_entity_id,
                account_id,
                party_id
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_journal_lines_party;

        ALTER TABLE journal_lines
            DROP COLUMN IF EXISTS party_id;
        """
    )
