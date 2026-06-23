"""add cost_center_id dimension to journal lines

Revision ID: 20260623_0011
Revises: 20260531_0010
Create Date: 2026-06-23

Purpose: add a nullable cost_center_id to posted journal lines so postings can
carry a cost-centre dimension (enterprise Cost-Centre Accounting add-on). Enables
cost-centre P&L and budget-vs-actual reporting that ties to the Trial Balance.
Affected table: journal_lines.
Tenant impact: additive only; existing rows keep NULL cost_center_id (appear as
"Unallocated" in cost-centre reports). No behaviour change for tenants that do
not enable the cost-centre add-on.
Backfill: none required.
Rollback: drop the cost-centre lookup index and the nullable cost_center_id column.
Destructive risk: no for upgrade; downgrade removes only this additive column.
Validation: compile accounting modules and run focused accounting tests.
"""

from alembic import op


revision = "20260623_0011"
down_revision = "20260531_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE journal_lines
            ADD COLUMN IF NOT EXISTS cost_center_id VARCHAR(64);

        CREATE INDEX IF NOT EXISTS ix_journal_lines_cost_center
            ON journal_lines(
                app_key,
                tenant_id,
                accounting_entity_id,
                cost_center_id,
                account_id
            );
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS ix_journal_lines_cost_center;

        ALTER TABLE journal_lines
            DROP COLUMN IF EXISTS cost_center_id;
        """
    )
