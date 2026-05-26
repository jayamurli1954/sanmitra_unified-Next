import pytest

from app.accounting.models import Account
from app.accounting.service import create_account, list_accounts, update_account


@pytest.mark.asyncio
async def test_update_account_name_is_tenant_scoped(async_session):
    await create_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="tenant-a",
        accounting_entity_id="primary",
        code="1010",
        name="Bank Account",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )
    await create_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="tenant-b",
        accounting_entity_id="primary",
        code="1010",
        name="Bank Account",
        account_type="asset",
        classification="real",
        is_cash_bank=True,
        is_receivable=False,
        is_payable=False,
    )

    updated = await update_account(
        async_session,
        app_key="gruhamitra",
        tenant_id="tenant-a",
        accounting_entity_id="primary",
        code="1010",
        name="HDFC Bank Current Account",
    )

    tenant_a_accounts = await list_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="tenant-a",
        accounting_entity_id="primary",
    )
    tenant_b_accounts = await list_accounts(
        async_session,
        app_key="gruhamitra",
        tenant_id="tenant-b",
        accounting_entity_id="primary",
    )

    assert updated.name == "HDFC Bank Current Account"
    assert [account.name for account in tenant_a_accounts] == ["HDFC Bank Current Account"]
    assert [account.name for account in tenant_b_accounts] == ["Bank Account"]

