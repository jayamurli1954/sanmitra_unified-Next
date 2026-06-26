from __future__ import annotations

from decimal import Decimal

import pytest

import app.modules.business.bulk_import as bulk_import


class _Journal:
    id = 77


class _Collection:
    def __init__(self, *, fail_insert: bool = False):
        self.fail_insert = fail_insert
        self.docs: list[dict] = []

    async def insert_one(self, doc):
        if self.fail_insert:
            raise RuntimeError("mongo write failed")
        self.docs.append(dict(doc))


@pytest.mark.asyncio
async def test_bulk_import_reverses_journal_when_voucher_persistence_fails(monkeypatch):
    preview = {
        "can_import": True,
        "format_type": "double_entry",
        "vouchers": [
            {
                "voucher_number": "JV-001",
                "voucher_type": "journal",
                "date": "2026-04-03",
                "amount": "12000.00",
                "description": "Inventory purchase adjustment",
                "debit_account_id": 11,
                "credit_account_id": 22,
                "party_id": None,
            }
        ],
    }
    reversal_box = {}

    async def _fake_preview(*args, **kwargs):
        return preview

    async def _fake_post(session, **kwargs):
        return _Journal(), True

    async def _fake_reverse(session, **kwargs):
        reversal_box.update(kwargs)
        return _Journal(), True

    monkeypatch.setattr(bulk_import, "build_bulk_import_preview", _fake_preview)
    monkeypatch.setattr(bulk_import, "post_journal_entry", _fake_post)
    monkeypatch.setattr(bulk_import, "reverse_journal_entry", _fake_reverse)
    monkeypatch.setattr(bulk_import, "get_collection", lambda name: _Collection(fail_insert=True))

    with pytest.raises(
        bulk_import.AccountingValidationError,
        match="automatically reversed",
    ):
        await bulk_import.post_bulk_import_vouchers(
            object(),
            tenant_id="t1",
            app_key="mitrabooks",
            accounting_entity_id="primary",
            csv_text="ignored",
            created_by="admin",
        )

    assert reversal_box["tenant_id"] == "t1"
    assert reversal_box["journal_id"] == 77
    assert reversal_box["app_key"] == "mitrabooks"
