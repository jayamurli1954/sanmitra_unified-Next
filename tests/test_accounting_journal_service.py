from datetime import date

import pytest

from app.accounting.service import AccountingValidationError, list_journal_entries


@pytest.mark.asyncio
async def test_list_journal_entries_rejects_reversed_date_range(async_session) -> None:
    with pytest.raises(AccountingValidationError, match="from_date cannot be greater than to_date"):
        await list_journal_entries(
            async_session,
            tenant_id="tenant-journal-range",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            from_date=date(2026, 5, 31),
            to_date=date(2026, 5, 1),
        )
