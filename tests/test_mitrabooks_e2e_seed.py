from decimal import Decimal

import pytest

from app.accounting.service import (
    get_accounts_payable,
    get_accounts_receivable,
    get_profit_loss,
    get_receipts_payments,
    get_trial_balance,
)
from app.modules.business import seed as business_seed
from app.modules.business import service as business_service

TENANT_ID = "tenant-mitrabooks-e2e-seed"
APP_KEY = "mitrabooks"
ACCOUNTING_ENTITY_ID = "primary"


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, field, direction):
        self.rows.sort(key=lambda row: row.get(field) or "", reverse=direction < 0)
        return self

    def limit(self, value):
        self.rows = self.rows[: int(value)]
        return self

    async def to_list(self, length):
        return self.rows[: int(length)]


class FakeCollection:
    def __init__(self):
        self.docs = []
        self.seq = 0

    async def create_index(self, *_args, **_kwargs):
        return None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, filters):
        for doc in self.docs:
            if self._matches(doc, filters):
                return dict(doc)
        return None

    async def count_documents(self, filters):
        return sum(1 for doc in self.docs if self._matches(doc, filters))

    async def find_one_and_update(self, filters, update, **_kwargs):
        self.seq += int(update.get("$inc", {}).get("seq", 1))
        for doc in self.docs:
            if self._matches(doc, filters):
                doc["seq"] = self.seq
                doc.update(update.get("$set", {}))
                return dict(doc)
        row = {**filters, "seq": self.seq}
        row.update(update.get("$setOnInsert", {}))
        row.update(update.get("$set", {}))
        self.docs.append(row)
        return dict(row)

    def find(self, filters):
        return FakeCursor([dict(doc) for doc in self.docs if self._matches(doc, filters)])

    async def update_one(self, filters, update):
        for doc in self.docs:
            if self._matches(doc, filters):
                doc.update(update.get("$set", {}))
                return None
        return None

    async def delete_one(self, filters):
        self.docs = [doc for doc in self.docs if not self._matches(doc, filters)]

    @staticmethod
    def _matches(doc, filters):
        return all(doc.get(key) == value for key, value in filters.items())


def _fake_business_collections() -> dict[str, FakeCollection]:
    return {
        business_service.PARTIES_COLLECTION: FakeCollection(),
        business_service.VOUCHERS_COLLECTION: FakeCollection(),
        business_service.VOUCHER_COUNTERS_COLLECTION: FakeCollection(),
        business_service.SALES_INVOICES_COLLECTION: FakeCollection(),
        business_service.CA_DOCUMENTS_COLLECTION: FakeCollection(),
    }


@pytest.mark.asyncio
async def test_mitrabooks_e2e_seed_creates_report_ready_business_tenant(async_session, monkeypatch):
    collections = _fake_business_collections()

    async def noop_audit_event(**_kwargs):
        return None

    # setdefault: the seed path touches auxiliary collections (invoice settings,
    # period locks, ...) that grow over time — back any unlisted name with an
    # empty FakeCollection instead of KeyError-ing on each new feature.
    monkeypatch.setattr(business_service, "get_collection", lambda name: collections.setdefault(name, FakeCollection()))
    monkeypatch.setattr(business_service, "log_audit_event", noop_audit_event)

    first = await business_seed.ensure_mitrabooks_e2e_seed(
        async_session,
        tenant_id=TENANT_ID,
        created_by="admin@mitrabooks.local",
    )
    second = await business_seed.ensure_mitrabooks_e2e_seed(
        async_session,
        tenant_id=TENANT_ID,
        created_by="admin@mitrabooks.local",
    )

    assert first["app_key"] == APP_KEY
    assert first["parties_total"] == 4
    assert first["parties_created"] == 4
    assert first["vouchers_created"] >= 5
    assert first["trial_balance"]["balanced"] is True
    assert first["profit_loss"]["income_total"] == "100000.00"
    assert first["profit_loss"]["expense_total"] == "62350.00"
    assert first["receivables_total"] == "88000.00"
    assert first["payables_total"] == "39000.00"
    assert "not yet implemented" in first["gap_note"]

    assert second["parties_created"] == 0
    assert second["journals_created"] == 0
    assert second["vouchers_created"] == 0

    parties = await business_service.list_parties(
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
    )
    vouchers = await business_service.list_vouchers(
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
    )
    trial_lines, trial_debit, trial_credit = await get_trial_balance(
        async_session,
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
        as_of=business_seed.SEED_DATE,
    )
    _pnl_lines, income_total, expense_total, net_profit = await get_profit_loss(
        async_session,
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
        from_date=business_seed.SEED_DATE,
        to_date=business_seed.SEED_DATE,
    )
    _rp_lines, total_receipts, total_payments, net_receipts = await get_receipts_payments(
        async_session,
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
        from_date=business_seed.SEED_DATE,
        to_date=business_seed.SEED_DATE,
    )
    _ar_lines, ar_total = await get_accounts_receivable(
        async_session,
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
        as_of=business_seed.SEED_DATE,
    )
    _ap_lines, ap_total = await get_accounts_payable(
        async_session,
        tenant_id=TENANT_ID,
        app_key=APP_KEY,
        accounting_entity_id=ACCOUNTING_ENTITY_ID,
        as_of=business_seed.SEED_DATE,
    )

    assert parties["total"] == 4
    assert vouchers["total"] == 6
    assert {voucher["reference"] for voucher in vouchers["items"]} >= {
        "E2E-OPENING-BANK",
        "E2E-REC-001",
        "E2E-PAY-001",
        "E2E-EXP-001",
        "E2E-BANK-CHG-001",
        "E2E-CONTRA-001",
    }
    assert len(trial_lines) >= 10
    assert trial_debit == trial_credit
    assert income_total == Decimal("100000.00")
    assert expense_total == Decimal("62350.00")
    assert net_profit == Decimal("37650.00")
    assert total_receipts == Decimal("535000.00")
    assert total_payments == Decimal("37350.00")
    assert net_receipts == Decimal("497650.00")
    assert ar_total == Decimal("88000.00")
    assert ap_total == Decimal("39000.00")
