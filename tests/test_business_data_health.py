from datetime import date

import pytest

from app.modules.business import data_health
from app.modules.business.bank_recon import BANK_RECON_MATCHES_COLLECTION, BANK_STATEMENT_LINES_COLLECTION
from app.modules.business.service import (
    CREDIT_NOTES_COLLECTION,
    DEBIT_NOTES_COLLECTION,
    PARTIES_COLLECTION,
    PURCHASE_BILLS_COLLECTION,
    SALES_INVOICES_COLLECTION,
    VOUCHERS_COLLECTION,
)


AS_OF = date(2026, 6, 30)
SCOPE = {"tenant_id": "tenant-a", "app_key": "mitrabooks", "accounting_entity_id": "primary"}


class _Cursor:
    def __init__(self, rows):
        self.rows = list(rows)

    async def to_list(self, length):
        return self.rows[:length]


class _Collection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def find(self, filters):
        return _Cursor([
            dict(row)
            for row in self.rows
            if all(row.get(key) == value for key, value in filters.items())
        ])


def _aging():
    return {
        "buckets_order": ["0-30", "31-60", "61-90", "90+"],
        "totals": {"0-30": "1000.00", "31-60": "500.00", "61-90": "0.00", "90+": "200.00"},
        "grand_total": "1700.00",
        "by_party": [
            {"party_id": "cust-a", "buckets": {"31-60": "500.00", "90+": "200.00"}, "total": "700.00"},
        ],
        "accounting_entity_id": "primary",
    }


def test_data_health_score_flags_all_target_rules():
    out = data_health.assemble_data_health_score(
        parties=[
            {**SCOPE, "party_id": "cust-a", "party_name": "Customer A", "party_type": "customer", "gstin": ""},
            {**SCOPE, "party_id": "vend-a", "party_name": "Vendor A", "party_type": "vendor", "gstin": "29ABCDE1234F1Z5"},
        ],
        documents={
            "sales_invoice": [
                {**SCOPE, "invoice_id": "inv-1", "invoice_number": "INV-001", "status": "posted"},
                {**SCOPE, "invoice_id": "inv-2", "invoice_number": "INV-001", "status": "posted"},
                {**SCOPE, "invoice_id": "inv-3", "invoice_number": "INV-002", "status": "draft"},
            ],
            "purchase_bill": [{**SCOPE, "bill_id": "bill-1", "bill_number": "BILL-001", "status": "pending_approval"}],
            "voucher": [],
            "credit_note": [],
            "debit_note": [],
        },
        statement_lines=[
            {**SCOPE, "statement_line_id": "stmt-old", "txn_date": "2026-05-01", "description": "Bank charge"},
            {**SCOPE, "statement_line_id": "stmt-matched", "txn_date": "2026-05-01"},
        ],
        recon_matches=[{**SCOPE, "statement_line_id": "stmt-matched", "status": "active"}],
        ar_aging=_aging(),
        as_of=AS_OF,
    )

    rules = {rule["key"]: rule for rule in out["rules"]}
    assert out["status"] == "needs_attention"
    assert out["score"] < 100
    assert rules["missing_gstin"]["count"] == 1
    assert rules["unposted_drafts"]["count"] == 2
    assert rules["duplicate_invoices"]["count"] == 1
    assert rules["stale_reconciliation"]["count"] == 1
    assert rules["overdue_exposure"]["severity"] == "danger"
    assert rules["overdue_exposure"]["evidence"][0]["over_90"] == "200.00"
    issues = {issue["issue_id"]: issue for issue in out["issues"]}
    assert out["issue_count"] == 6
    assert issues["data-health:missing_gstin:business_party:cust-a"]["workspace"] == "parties"
    assert issues["data-health:unposted_drafts:business_sales_invoice:inv-3"]["action_label"] == "Open Sales"
    assert issues["data-health:unposted_drafts:business_purchase_bill:bill-1"]["workspace"] == "bills"
    assert issues["data-health:duplicate_invoices:business_sales_invoice:inv-001"]["workspace"] == "sales"
    assert issues["data-health:stale_reconciliation:bank_statement_line:stmt-old"]["action_label"] == "Open Bank Reconciliation"
    assert issues["data-health:overdue_exposure:receivables_aging:receivables-aging"]["workspace"] == "financial-health"


@pytest.mark.asyncio
async def test_data_health_builder_reads_tenant_scoped_collections(monkeypatch):
    collections = {
        PARTIES_COLLECTION: _Collection([
            {**SCOPE, "party_id": "cust-a", "party_name": "Customer A", "party_type": "customer", "gstin": ""},
            {**SCOPE, "tenant_id": "tenant-b", "party_id": "cust-b", "party_type": "customer", "gstin": ""},
        ]),
        SALES_INVOICES_COLLECTION: _Collection([
            {**SCOPE, "invoice_id": "inv-1", "invoice_number": "INV-001", "status": "posted"},
            {**SCOPE, "invoice_id": "inv-2", "invoice_number": "INV-001", "status": "posted"},
            {**SCOPE, "tenant_id": "tenant-b", "invoice_id": "inv-x", "invoice_number": "INV-001", "status": "draft"},
        ]),
        PURCHASE_BILLS_COLLECTION: _Collection(),
        VOUCHERS_COLLECTION: _Collection([{**SCOPE, "voucher_id": "v-1", "voucher_number": "JV-001", "status": "draft"}]),
        CREDIT_NOTES_COLLECTION: _Collection(),
        DEBIT_NOTES_COLLECTION: _Collection(),
        BANK_STATEMENT_LINES_COLLECTION: _Collection([{**SCOPE, "statement_line_id": "stmt-old", "txn_date": "2026-05-01"}]),
        BANK_RECON_MATCHES_COLLECTION: _Collection(),
    }

    def _get_collection(name):
        return collections.setdefault(name, _Collection())

    async def _fake_aging(**kwargs):
        assert kwargs["tenant_id"] == "tenant-a"
        assert kwargs["app_key"] == "mitrabooks"
        assert kwargs["accounting_entity_id"] == "primary"
        assert kwargs["kind"] == "receivable"
        return _aging()

    monkeypatch.setattr(data_health, "get_collection", _get_collection)
    monkeypatch.setattr(data_health.allocation_service, "ar_ap_aging", _fake_aging)

    out = await data_health.build_data_health_score(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary", as_of=AS_OF,
    )

    rules = {rule["key"]: rule for rule in out["rules"]}
    assert rules["missing_gstin"]["count"] == 1
    assert rules["duplicate_invoices"]["count"] == 1
    assert rules["unposted_drafts"]["count"] == 1
    assert rules["stale_reconciliation"]["count"] == 1
    assert all(issue["entity_id"] != "inv-x" for issue in out["issues"])
    assert {issue["workspace"] for issue in out["issues"]} >= {"parties", "sales", "vouchers", "bank-recon", "financial-health"}
