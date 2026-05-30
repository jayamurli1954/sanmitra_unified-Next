"""add account name index for COA lookup

Revision ID: 20260530_0009
Revises: 20260527_0008
Create Date: 2026-05-30

Phase 1 (MitraBooks ERP core): the chart of accounts is searched by both code
and name. The account ``code`` already has a unique constraint
(``uq_accounts_app_tenant_entity_code``); this migration adds a tenant/entity
scoped index on ``name`` so COA name lookup and search are indexed too.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260530_0009"
down_revision = "20260527_0008"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_accounts_app_tenant_entity_name"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "accounts",
        ["app_key", "tenant_id", "accounting_entity_id", "name"],
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="accounts")
