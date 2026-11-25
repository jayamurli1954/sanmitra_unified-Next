"""Bank reconciliation — CSV statement parsing, match suggestion and the BRS
assembler. Pure functions, no DB. Sign convention under test: a statement
DEPOSIT corresponds to a book DEBIT on the bank account (asset increases)."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.accounting.service import AccountingNotFoundError, AccountingValidationError
from app.modules.business import bank_recon
from app.modules.business.bank_recon import (
    BANK_RECON_MATCHES_COLLECTION,
    BANK_STATEMENT_LINES_COLLECTION,
    assemble_bank_reconciliation,
    parse_bank_statement_csv,
    plan_difference_adjustment,
    statement_line_dedupe_key,
    suggest_difference_matches,
    suggest_group_matches,
    suggest_matches,
    validate_group_match,
)


# ---- CSV parsing ---------------------------------------------------------- #

def test_parse_two_column_csv_with_common_headers():
    csv_text = (
        "Txn Date,Narration,Chq No,Withdrawal Amt,Deposit Amt,Balance\n"
        "01/04/2026,NEFT FROM ACME,UTR123,,\"50,000.00\",\"1,50,000.00\"\n"
        "03/04/2026,CHQ PAID RENT,000451,25000,,125000\n"
        "  ,Opening Balance,,,,100000\n"          # no date -> skipped
        "05/04/2026,ZERO ROW,,0,0,125000\n"       # zero movement -> skipped
    )
    lines = parse_bank_statement_csv(csv_text)
    assert len(lines) == 2
    assert lines[0] == {
        "txn_date": "2026-04-01", "description": "NEFT FROM ACME", "ref": "UTR123",
        "withdrawal": "0.00", "deposit": "50000.00", "balance": "150000.00",
    }
    assert lines[1]["withdrawal"] == "25000.00"
    assert lines[1]["deposit"] == "0.00"
    assert lines[1]["txn_date"] == "2026-04-03"


def test_parse_single_amount_with_drcr_column_and_date_variants():
    csv_text = (
        "Date,Particulars,Amount,Dr/Cr\n"
        "2026-04-01,UPI received,1500.50,CR\n"
        "02-Apr-2026,Bank charges,118.00,DR\n"
    )
    lines = parse_bank_statement_csv(csv_text)
    assert lines[0]["deposit"] == "1500.50"
    assert lines[1]["withdrawal"] == "118.00"
    assert lines[1]["txn_date"] == "2026-04-02"


def test_parse_signed_single_amount_column():
    csv_text = "date,description,amount\n01/04/2026,salary out,-30000\n01/04/2026,client in,45000\n"
    lines = parse_bank_statement_csv(csv_text)
    assert lines[0]["withdrawal"] == "30000.00"
    assert lines[1]["deposit"] == "45000.00"


def test_parse_rejects_unusable_files():
    with pytest.raises(ValueError):
        parse_bank_statement_csv("")
    with pytest.raises(ValueError):
        parse_bank_statement_csv("foo,bar\n1,2\n")  # no date column
    with pytest.raises(ValueError):
        parse_bank_statement_csv("date,notes\n01/04/2026,hello\n")  # no amounts


def test_dedupe_key_stable_and_distinguishing():
    a = {"txn_date": "2026-04-01", "withdrawal": "0.00", "deposit": "500.00", "ref": "U1", "description": "NEFT"}
    assert statement_line_dedupe_key(a) == statement_line_dedupe_key(dict(a))
    assert statement_line_dedupe_key(a) != statement_line_dedupe_key({**a, "deposit": "501.00"})


# ---- Matching ------------------------------------------------------------- #

def _stmt(id_, d, *, deposit="0.00", withdrawal="0.00", ref="", desc=""):
    return {"statement_line_id": id_, "txn_date": d, "deposit": deposit,
            "withdrawal": withdrawal, "ref": ref, "description": desc}


def _book(line_id, d, *, debit="0.00", credit="0.00", reference="", description=""):
    return {"line_id": line_id, "journal_id": 100 + line_id, "entry_date": d,
            "debit": debit, "credit": credit, "reference": reference, "description": description}


def test_suggest_matches_amount_side_and_window():
    suggestions = suggest_matches(
        [
            _stmt("s1", "2026-04-03", deposit="5000.00"),            # matches book debit 2 days earlier
            _stmt("s2", "2026-04-10", withdrawal="2000.00"),          # matches book credit same day
            _stmt("s3", "2026-04-20", deposit="999.00"),              # no book counterpart
            _stmt("s4", "2026-04-01", deposit="7000.00"),             # book line is 30 days away -> outside window
        ],
        [
            _book(1, "2026-04-01", debit="5000.00"),
            _book(2, "2026-04-10", credit="2000.00"),
            _book(3, "2026-05-01", debit="7000.00"),
            _book(4, "2026-04-03", credit="5000.00"),  # wrong side for s1 (deposit needs debit)
        ],
    )
    by_stmt = {s["statement_line_id"]: s for s in suggestions}
    assert set(by_stmt) == {"s1", "s2"}
    assert by_stmt["s1"]["line_id"] == 1 and by_stmt["s1"]["date_diff_days"] == 2
    assert by_stmt["s2"]["side"] == "withdrawal"


def test_suggest_matches_prefers_reference_hit_and_is_one_to_one():
    suggestions = suggest_matches(
        [_stmt("s1", "2026-04-05", deposit="1000.00", ref="INV-77")],
        [
            _book(1, "2026-04-05", debit="1000.00", reference="misc"),
            _book(2, "2026-04-07", debit="1000.00", reference="Receipt INV-77"),
        ],
    )
    # The ref match wins even though the other candidate's date is closer.
    assert len(suggestions) == 1
    assert suggestions[0]["line_id"] == 2
    assert suggestions[0]["confidence"] == "ref"


# ---- BRS assembly --------------------------------------------------------- #

def test_brs_identity_and_classification():
    account = {"account_id": 7, "code": "11010", "name": "Bank Account"}
    statement_lines = [
        _stmt("s1", "2026-04-01", deposit="50000.00") | {"balance": "50000.00"},
        _stmt("s2", "2026-04-05", withdrawal="118.00", desc="bank charges") | {"balance": "49882.00"},
    ]
    ledger_lines = [
        _book(1, "2026-04-01", debit="50000.00"),    # matched to s1
        _book(2, "2026-04-06", credit="25000.00"),   # cheque issued, not presented
    ]
    matches = [{"statement_line_id": "s1", "line_id": "1", "journal_id": 101, "amount": "50000.00"}]
    out = assemble_bank_reconciliation(
        account=account, as_of=date(2026, 4, 30),
        statement_lines=statement_lines, ledger_lines=ledger_lines,
        matches=matches, suggestions=[],
    )
    s = out["summary"]
    # Book balance = 50000 - 25000 = 25000.
    assert s["book_balance"] == "25000.00"
    # Expected statement = book 25000 + uncleared credit 25000 - 0 + 0 - bank-only 118 = 49882.
    assert s["expected_statement_balance"] == "49882.00"
    assert s["statement_balance"] == "49882.00"
    assert s["difference"] == "0.00"
    assert [l["statement_line_id"] for l in out["in_bank_not_in_books"]] == ["s2"]
    assert [l["line_id"] for l in out["in_books_not_in_bank"]] == [2]
    assert s["uncleared_withdrawals"] == "25000.00"
    assert s["bank_only_withdrawals"] == "118.00"


def test_brs_without_statement_balance_column():
    out = assemble_bank_reconciliation(
        account={"account_id": 7, "code": "11010", "name": "Bank"},
        as_of=date(2026, 4, 30),
        statement_lines=[_stmt("s1", "2026-04-01", deposit="100.00")],
        ledger_lines=[], matches=[], suggestions=[],
    )
    assert out["summary"]["statement_balance"] is None
    assert out["summary"]["difference"] is None
    assert out["summary"]["expected_statement_balance"] == "100.00"


class _FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)

    def sort(self, field, direction):
        self.rows.sort(key=lambda row: row.get(field), reverse=direction < 0)
        return self

    async def to_list(self, length):
        return self.rows[:length]


class _FakeCollection:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    @staticmethod
    def _matches(row, query):
        for key, expected in query.items():
            actual = row.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]:
                    return False
                continue
            if actual != expected:
                return False
        return True

    async def find_one(self, query):
        return next((row for row in self.rows if self._matches(row, query)), None)

    def find(self, query, projection=None):
        rows = [row for row in self.rows if self._matches(row, query)]
        if projection:
            keys = {key for key, include in projection.items() if include}
            rows = [{key: row.get(key) for key in keys if key in row} for row in rows]
        return _FakeCursor(rows)

    async def insert_one(self, doc):
        self.rows.append(doc)
        return SimpleNamespace(inserted_id=doc.get("match_id") or doc.get("statement_line_id"))

    async def insert_many(self, docs):
        self.rows.extend(docs)
        return SimpleNamespace(inserted_ids=[doc.get("statement_line_id") for doc in docs])

    async def update_one(self, query, update):
        row = await self.find_one(query)
        if row is not None:
            row.update(update.get("$set", {}))
        return SimpleNamespace(matched_count=1 if row else 0, modified_count=1 if row else 0)

    async def update_many(self, query, update):
        rows = [row for row in self.rows if self._matches(row, query)]
        for row in rows:
            row.update(update.get("$set", {}))
        return SimpleNamespace(matched_count=len(rows), modified_count=len(rows))


@pytest.fixture
def fake_bank_collections(monkeypatch):
    collections = {}

    def _get_collection(name):
        return collections.setdefault(name, _FakeCollection())

    monkeypatch.setattr("app.db.mongo.get_collection", _get_collection)
    monkeypatch.setattr("app.core.audit.service.get_collection", _get_collection)
    return collections


def _scope(tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary"):
    return {"tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": accounting_entity_id}


def _ledger_service(lines):
    account = SimpleNamespace(id=102, code="11010", name="Bank Account")

    async def _fake_get_ledger_lines(session, *, tenant_id, account_id, app_key, accounting_entity_id):
        assert tenant_id == "tenant-a"
        assert app_key == "mitrabooks"
        assert accounting_entity_id == "primary"
        assert account_id == 102
        return account, list(lines)

    return _fake_get_ledger_lines


@pytest.mark.asyncio
async def test_upload_bank_statement_is_scoped_and_dedupes(fake_bank_collections):
    csv_text = (
        "Txn Date,Narration,Ref No,Withdrawal,Deposit,Balance\n"
        "01/04/2026,NEFT FROM ACME,UTR123,,50000,150000\n"
        "03/04/2026,BANK CHARGES,CHG001,118,,149882\n"
    )

    first = await bank_recon.upload_bank_statement(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, csv_text=csv_text, created_by="tester",
    )
    second = await bank_recon.upload_bank_statement(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, csv_text=csv_text, created_by="tester",
    )
    other_tenant = await bank_recon.upload_bank_statement(
        tenant_id="tenant-b", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, csv_text=csv_text, created_by="tester",
    )

    assert first["inserted"] == 2
    assert first["skipped_duplicates"] == 0
    assert second["inserted"] == 0
    assert second["skipped_duplicates"] == 2
    assert other_tenant["inserted"] == 2
    stored = fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION].rows
    assert sum(1 for row in stored if row["tenant_id"] == "tenant-a") == 2
    assert sum(1 for row in stored if row["tenant_id"] == "tenant-b") == 2


@pytest.mark.asyncio
async def test_upload_bank_statement_writes_import_audit_event(fake_bank_collections):
    csv_text = (
        "Txn Date,Narration,Ref No,Withdrawal,Deposit,Balance\n"
        "01/04/2026,NEFT FROM ACME,UTR123,,50000,150000\n"
        "03/04/2026,BANK CHARGES,CHG001,118,,149882\n"
    )

    await bank_recon.upload_bank_statement(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, csv_text=csv_text, created_by="tester",
    )
    # Re-upload the same rows: import is a dedupe no-op but still audited.
    await bank_recon.upload_bank_statement(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, csv_text=csv_text, created_by="tester",
    )

    audit_rows = fake_bank_collections["core_audit_logs"].rows
    imported = [r for r in audit_rows if r.get("action") == "business_bank_statement_imported"]
    assert len(imported) == 2

    first_event = imported[0]
    assert first_event["tenant_id"] == "tenant-a"
    assert first_event["user_id"] == "tester"
    assert first_event["product"] == "mitrabooks"
    assert first_event["entity_type"] == "business_bank_statement_import"
    assert first_event["new_value"]["provider"] == "csv"
    assert first_event["new_value"]["account_id"] == 102
    assert first_event["new_value"]["inserted"] == 2
    assert first_event["new_value"]["skipped_duplicates"] == 0

    # Second import recorded the dedupe outcome (nothing inserted, both skipped).
    assert imported[1]["new_value"]["inserted"] == 0
    assert imported[1]["new_value"]["skipped_duplicates"] == 2


@pytest.mark.asyncio
async def test_build_bank_reconciliation_uses_same_scope_rows_and_active_matches(fake_bank_collections, monkeypatch):
    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION] = _FakeCollection([
        {
            **_scope(), "account_id": 102, "statement_line_id": "s-matched",
            "txn_date": "2026-04-01", "description": "NEFT FROM ACME", "ref": "UTR123",
            "withdrawal": "0.00", "deposit": "50000.00", "balance": "50000.00",
        },
        {
            **_scope(), "account_id": 102, "statement_line_id": "s-open",
            "txn_date": "2026-04-03", "description": "CLIENT RECEIPT", "ref": "INV-88",
            "withdrawal": "0.00", "deposit": "7500.00", "balance": "57500.00",
        },
        {
            **_scope("tenant-b"), "account_id": 102, "statement_line_id": "s-other-tenant",
            "txn_date": "2026-04-03", "description": "OTHER TENANT", "ref": "",
            "withdrawal": "0.00", "deposit": "9999.00", "balance": "9999.00",
        },
    ])
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection([
        {
            **_scope(), "match_id": "m1", "account_id": 102,
            "statement_line_id": "s-matched", "line_id": 1, "journal_id": 101,
            "side": "deposit", "amount": "50000.00", "status": "active",
        },
        {
            **_scope(), "match_id": "m-reversed", "account_id": 102,
            "statement_line_id": "s-old", "line_id": 99, "journal_id": 199,
            "side": "deposit", "amount": "1.00", "status": "reversed",
        },
    ])
    monkeypatch.setattr("app.accounting.service.get_ledger_lines", _ledger_service([
        _book(1, "2026-04-01", debit="50000.00", reference="UTR123"),
        _book(2, "2026-04-04", debit="7500.00", reference="Receipt INV-88"),
        _book(3, "2026-05-01", debit="9999.00", reference="future"),
    ]))

    out = await bank_recon.build_bank_reconciliation(
        object(), tenant_id="tenant-a", app_key="mitrabooks",
        accounting_entity_id="primary", account_id=102, as_of=date(2026, 4, 30),
    )

    assert out["summary"]["matched_count"] == 1
    assert out["summary"]["statement_lines_total"] == 2
    assert out["summary"]["book_lines_total"] == 2
    assert [row["statement_line_id"] for row in out["in_bank_not_in_books"]] == ["s-open"]
    assert [row["line_id"] for row in out["in_books_not_in_bank"]] == [2]
    assert len(out["suggestions"]) == 1
    assert out["suggestions"][0]["statement_line_id"] == "s-open"
    assert out["suggestions"][0]["line_id"] == 2
    assert out["suggestions"][0]["confidence"] == "ref"


@pytest.mark.asyncio
async def test_create_bank_recon_match_validates_scope_amount_side_and_duplicates(fake_bank_collections, monkeypatch):
    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION] = _FakeCollection([
        {
            **_scope(), "account_id": 102, "statement_line_id": "s1",
            "txn_date": "2026-04-01", "description": "NEFT FROM ACME", "ref": "UTR123",
            "withdrawal": "0.00", "deposit": "50000.00", "balance": "50000.00",
        },
        {
            **_scope("tenant-b"), "account_id": 102, "statement_line_id": "s-other",
            "txn_date": "2026-04-01", "withdrawal": "0.00", "deposit": "50000.00",
        },
    ])
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection()
    monkeypatch.setattr("app.accounting.service.get_ledger_lines", _ledger_service([
        _book(1, "2026-04-01", debit="50000.00", reference="UTR123"),
        _book(2, "2026-04-02", credit="50000.00", reference="wrong side"),
    ]))

    match = await bank_recon.create_bank_recon_match(
        object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, statement_line_id="s1", line_id=1, created_by="tester",
    )

    assert match["status"] == "active"
    assert match["side"] == "deposit"
    assert match["amount"] == "50000.00"
    assert match["tenant_id"] == "tenant-a"

    with pytest.raises(AccountingValidationError, match="already matched"):
        await bank_recon.create_bank_recon_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="s1", line_id=1, created_by="tester",
        )

    with pytest.raises(AccountingValidationError, match="Statement line not found"):
        await bank_recon.create_bank_recon_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="s-other", line_id=1, created_by="tester",
        )

    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION].rows[0]["statement_line_id"] = "s2"
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows.clear()
    with pytest.raises(AccountingValidationError, match="Amounts do not agree"):
        await bank_recon.create_bank_recon_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="s2", line_id=2, created_by="tester",
        )


@pytest.mark.asyncio
async def test_reverse_bank_recon_match_is_soft_and_scoped(fake_bank_collections):
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection([
        {**_scope(), "match_id": "m1", "status": "active", "account_id": 102},
        {**_scope("tenant-b"), "match_id": "m2", "status": "active", "account_id": 102},
    ])

    result = await bank_recon.reverse_bank_recon_match(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        match_id="m1", reversed_by="tester",
    )

    assert result == {"match_id": "m1", "status": "reversed"}
    row = fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows[0]
    assert row["status"] == "reversed"
    assert row["reversed_by"] == "tester"

    with pytest.raises(AccountingValidationError, match="already reversed"):
        await bank_recon.reverse_bank_recon_match(
            tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            match_id="m1", reversed_by="tester",
        )

    with pytest.raises(AccountingNotFoundError, match="Match not found"):
        await bank_recon.reverse_bank_recon_match(
            tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            match_id="m2", reversed_by="tester",
        )


@pytest.mark.asyncio
async def test_post_bank_statement_line_voucher_posts_with_correct_direction_and_marks_line(fake_bank_collections, monkeypatch):
    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION] = _FakeCollection([
        {
            **_scope(), "account_id": 102, "statement_line_id": "stmt-charge",
            "txn_date": "2026-04-02", "description": "BANK CHARGES", "ref": "CHG-118",
            "withdrawal": "118.00", "deposit": "0.00",
        }
    ])
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection()
    calls = {}

    async def fake_post_typed_voucher(session, *, tenant_id, app_key, created_by, payload, idempotency_key):
        calls["post"] = {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "created_by": created_by,
            "payload": payload,
            "idempotency_key": idempotency_key,
        }
        return {
            "voucher_id": "voucher-1",
            "voucher_number": "JV-1",
            "voucher_type": "journal",
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": payload.accounting_entity_id,
            "amount": payload.amount,
            "entry_date": payload.entry_date,
            "debit_account_id": 51001,
            "credit_account_id": 102,
            "description": payload.description,
            "reference": payload.reference,
            "status": "pending_approval",
            "created": True,
            "created_by": created_by,
            "created_at": "2026-04-02T00:00:00+00:00",
            "updated_at": "2026-04-02T00:00:00+00:00",
        }

    async def fake_review_typed_voucher(session, *, tenant_id, app_key, voucher_id, reviewed_by, payload):
        calls["review"] = {
            "tenant_id": tenant_id,
            "app_key": app_key,
            "voucher_id": voucher_id,
            "reviewed_by": reviewed_by,
            "payload": payload,
        }
        voucher = dict(calls["post_result"])
        voucher.update({"status": "posted", "journal_entry_id": 9001})
        return voucher

    async def fake_post_and_store(*args, **kwargs):
        result = await fake_post_typed_voucher(*args, **kwargs)
        calls["post_result"] = result
        return result

    monkeypatch.setattr("app.modules.business.service.post_typed_voucher", fake_post_and_store)
    monkeypatch.setattr("app.modules.business.service.review_typed_voucher", fake_review_typed_voucher)

    out = await bank_recon.post_bank_statement_line_voucher(
        object(),
        tenant_id="tenant-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        account_id=102,
        statement_line_id="stmt-charge",
        offset_account_id=51001,
        offset_account_code=None,
        description=None,
        reference=None,
        approve=True,
        created_by="tester",
        idempotency_key="bank-charge-key",
    )

    payload = calls["post"]["payload"]
    assert payload.voucher_type == "journal"
    assert payload.entry_date.isoformat() == "2026-04-02"
    assert payload.amount == Decimal("118.00")
    assert payload.debit_account_id == 51001
    assert payload.credit_account_id == 102
    assert payload.reference == "CHG-118"
    assert calls["post"]["idempotency_key"] == "bank-charge-key"
    assert calls["review"]["payload"].approve is True
    assert out["posting_status"] == "posted"
    assert out["voucher"]["journal_entry_id"] == 9001
    stored = fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION].rows[0]
    assert stored["posted_voucher_id"] == "voucher-1"
    assert stored["posted_journal_entry_id"] == 9001
    assert stored["posting_status"] == "posted"


@pytest.mark.asyncio
async def test_post_bank_statement_line_voucher_deposit_credits_offset_and_rejects_duplicates(fake_bank_collections, monkeypatch):
    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION] = _FakeCollection([
        {
            **_scope(), "account_id": 102, "statement_line_id": "stmt-interest",
            "txn_date": "2026-04-03", "description": "BANK INTEREST", "ref": "INT-1",
            "withdrawal": "0.00", "deposit": "250.00",
        },
        {
            **_scope(), "account_id": 102, "statement_line_id": "stmt-posted",
            "txn_date": "2026-04-03", "withdrawal": "0.00", "deposit": "25.00",
            "posted_voucher_id": "existing-voucher",
        },
        {
            **_scope("tenant-b"), "account_id": 102, "statement_line_id": "stmt-other",
            "txn_date": "2026-04-03", "withdrawal": "0.00", "deposit": "250.00",
        },
    ])
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection([
        {**_scope(), "account_id": 102, "statement_line_id": "stmt-matched", "status": "active"}
    ])
    calls = {}

    async def fake_post_typed_voucher(session, *, tenant_id, app_key, created_by, payload, idempotency_key):
        calls["payload"] = payload
        return {
            "voucher_id": "voucher-interest",
            "voucher_number": "JV-2",
            "voucher_type": "journal",
            "tenant_id": tenant_id,
            "app_key": app_key,
            "accounting_entity_id": payload.accounting_entity_id,
            "amount": payload.amount,
            "entry_date": payload.entry_date,
            "debit_account_id": 102,
            "credit_account_id": 41001,
            "description": payload.description,
            "reference": payload.reference,
            "status": "pending_approval",
            "created": True,
            "created_by": created_by,
            "created_at": "2026-04-03T00:00:00+00:00",
            "updated_at": "2026-04-03T00:00:00+00:00",
        }

    monkeypatch.setattr("app.modules.business.service.post_typed_voucher", fake_post_typed_voucher)

    out = await bank_recon.post_bank_statement_line_voucher(
        object(),
        tenant_id="tenant-a",
        app_key="mitrabooks",
        accounting_entity_id="primary",
        account_id=102,
        statement_line_id="stmt-interest",
        offset_account_id=41001,
        offset_account_code=None,
        description="Interest income from bank statement",
        reference=None,
        approve=False,
        created_by="tester",
        idempotency_key=None,
    )

    assert calls["payload"].debit_account_id == 102
    assert calls["payload"].credit_account_id == 41001
    assert calls["payload"].description == "Interest income from bank statement"
    assert out["posting_status"] == "pending_approval"

    with pytest.raises(AccountingValidationError, match="already has a voucher"):
        await bank_recon.post_bank_statement_line_voucher(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="stmt-posted", offset_account_id=41001,
            offset_account_code=None, description=None, reference=None, approve=False,
            created_by="tester", idempotency_key=None,
        )

    with pytest.raises(AccountingValidationError, match="Statement line not found"):
        await bank_recon.post_bank_statement_line_voucher(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="stmt-other", offset_account_id=41001,
            offset_account_code=None, description=None, reference=None, approve=False,
            created_by="tester", idempotency_key=None,
        )


# ---- Group (one-to-many / many-to-one) matching ---------------------------- #

def test_group_suggestion_one_deposit_covers_several_receipts():
    # A deposit slip of 15,000 covering two customer receipts; a 7,000 decoy
    # and a wrong-side 5,000 must not be used.
    out = suggest_group_matches(
        [_stmt("s1", "2026-04-05", deposit="15000.00", desc="CASH DEP SLIP 44")],
        [
            _book(1, "2026-04-03", debit="10000.00", reference="RCPT-1"),
            _book(2, "2026-04-04", debit="5000.00", reference="RCPT-2"),
            _book(3, "2026-04-04", debit="7000.00", reference="RCPT-3"),
            _book(4, "2026-04-04", credit="5000.00", reference="PAY-9"),
        ],
    )
    assert len(out) == 1
    g = out[0]
    assert g["group_type"] == "one_to_many"
    assert g["side"] == "deposit"
    assert g["amount"] == "15000.00"
    assert g["statement_line_ids"] == ["s1"]
    assert sorted(g["line_ids"]) == [1, 2]
    assert g["confidence"] == "exact_sum"
    assert g["max_date_diff_days"] == 2
    assert sum(Decimal(b["amount"]) for b in g["book"]) == Decimal("15000.00")


def test_group_suggestion_bank_split_one_payment_into_several_debits():
    out = suggest_group_matches(
        [
            _stmt("s1", "2026-04-10", withdrawal="200000.00", desc="IMPS 1/2"),
            _stmt("s2", "2026-04-10", withdrawal="100000.00", desc="IMPS 2/2"),
        ],
        [_book(1, "2026-04-09", credit="300000.00", reference="PAY-VENDOR")],
    )
    assert len(out) == 1
    g = out[0]
    assert g["group_type"] == "many_to_one"
    assert g["side"] == "withdrawal"
    assert sorted(g["statement_line_ids"]) == ["s1", "s2"]
    assert g["line_ids"] == [1]


def test_group_suggestion_respects_window_exclusions_and_strictly_smaller_parts():
    stmt = [_stmt("s1", "2026-04-05", deposit="1000.00")]
    # One part is 20 days away -> outside the window, so no exact subset remains.
    assert suggest_group_matches(stmt, [
        _book(1, "2026-04-05", debit="600.00"),
        _book(2, "2026-04-25", debit="400.00"),
    ]) == []
    # Lines already taken by the 1:1 pass are excluded.
    assert suggest_group_matches(stmt, [
        _book(1, "2026-04-05", debit="600.00"),
        _book(2, "2026-04-05", debit="400.00"),
    ], exclude_line_ids={"2"}) == []
    assert suggest_group_matches(stmt, [
        _book(1, "2026-04-05", debit="600.00"),
        _book(2, "2026-04-05", debit="400.00"),
    ], exclude_statement_ids={"s1"}) == []
    # An equal-amount line is a 1:1 match, never part of a group.
    assert suggest_group_matches(stmt, [_book(1, "2026-04-05", debit="1000.00")]) == []


def test_group_suggestion_prefers_fewest_lines_and_flags_ambiguity():
    # 600+400 (2 lines) beats 300+300+400 (3 lines); both exist -> ambiguous.
    out = suggest_group_matches(
        [_stmt("s1", "2026-04-05", deposit="1000.00")],
        [
            _book(1, "2026-04-05", debit="600.00"),
            _book(2, "2026-04-05", debit="400.00"),
            _book(3, "2026-04-05", debit="300.00"),
            _book(4, "2026-04-05", debit="300.00"),
        ],
    )
    assert len(out) == 1
    assert sorted(out[0]["line_ids"]) == [1, 2]
    assert out[0]["confidence"] == "ambiguous"


def test_group_suggestion_never_reuses_a_line_across_groups():
    out = suggest_group_matches(
        [
            _stmt("s1", "2026-04-05", deposit="900.00"),
            _stmt("s2", "2026-04-06", deposit="900.00"),
        ],
        [
            _book(1, "2026-04-05", debit="500.00"),
            _book(2, "2026-04-05", debit="400.00"),
            _book(3, "2026-04-06", debit="450.00"),
            _book(4, "2026-04-06", debit="450.00"),
        ],
    )
    used = [line_id for g in out for line_id in g["line_ids"]]
    assert len(used) == len(set(used)) == 4
    assert {g["statement_line_ids"][0] for g in out} == {"s1", "s2"}


def test_group_suggestion_search_is_bounded_on_pathological_input():
    # 40 identical small receipts and a target no subset of <=4 can reach.
    books = [_book(i, "2026-04-05", debit="1.00") for i in range(1, 41)]
    assert suggest_group_matches([_stmt("s1", "2026-04-05", deposit="999.00")], books) == []


def test_validate_group_match_rules():
    s1 = _stmt("s1", "2026-04-05", deposit="1000.00")
    s2 = _stmt("s2", "2026-04-05", deposit="500.00")
    b_600 = {"debit": "600.00", "credit": "0.00"}
    b_400 = {"debit": "400.00", "credit": "0.00"}
    assert validate_group_match([s1], [b_600, b_400]) == ("one_to_many", "deposit", Decimal("1000.00"))
    assert validate_group_match([s2, _stmt("s3", "2026-04-05", deposit="100.00")], [{"debit": "600.00"}]) == (
        "many_to_one", "deposit", Decimal("600.00"),
    )
    with pytest.raises(ValueError, match="single match"):
        validate_group_match([s1], [b_600])
    with pytest.raises(ValueError, match="Many-to-many"):
        validate_group_match([s1, s2], [b_600, b_400])
    with pytest.raises(ValueError, match="Totals do not agree"):
        validate_group_match([s1], [b_600, {"debit": "300.00"}])
    with pytest.raises(ValueError, match="same direction"):
        validate_group_match([s1], [b_600, {"credit": "400.00"}])
    with pytest.raises(ValueError, match="at most"):
        validate_group_match([s1], [{"debit": "10.00"}] * 11)


def test_brs_identity_holds_with_group_matches():
    statement_lines = [_stmt("s1", "2026-04-05", deposit="15000.00") | {"balance": "15000.00"}]
    ledger_lines = [
        _book(1, "2026-04-03", debit="10000.00"),
        _book(2, "2026-04-04", debit="5000.00"),
    ]
    matches = [
        {"match_id": "m1", "match_group_id": "g1", "statement_line_id": "s1", "line_id": 1, "amount": "10000.00"},
        {"match_id": "m2", "match_group_id": "g1", "statement_line_id": "s1", "line_id": 2, "amount": "5000.00"},
    ]
    out = assemble_bank_reconciliation(
        account={"account_id": 7, "code": "11010", "name": "Bank"}, as_of=date(2026, 4, 30),
        statement_lines=statement_lines, ledger_lines=ledger_lines, matches=matches, suggestions=[],
    )
    assert out["summary"]["difference"] == "0.00"
    assert out["summary"]["matched_groups"] == 1
    assert out["in_bank_not_in_books"] == []
    assert out["in_books_not_in_bank"] == []
    assert out["group_suggestions"] == []


def _group_fixture(fake_bank_collections, monkeypatch, matches=None):
    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION] = _FakeCollection([
        {**_scope(), "account_id": 102, "statement_line_id": "s1", "txn_date": "2026-04-05",
         "description": "CASH DEP SLIP 44", "ref": "", "withdrawal": "0.00", "deposit": "15000.00"},
        {**_scope(), "account_id": 102, "statement_line_id": "s2", "txn_date": "2026-04-06",
         "description": "BANK CHG", "ref": "", "withdrawal": "118.00", "deposit": "0.00"},
        {**_scope("tenant-b"), "account_id": 102, "statement_line_id": "s-other", "txn_date": "2026-04-05",
         "withdrawal": "0.00", "deposit": "15000.00"},
    ])
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection(matches or [])
    monkeypatch.setattr("app.accounting.service.get_ledger_lines", _ledger_service([
        _book(1, "2026-04-03", debit="10000.00", reference="RCPT-1"),
        _book(2, "2026-04-04", debit="5000.00", reference="RCPT-2"),
        _book(3, "2026-04-04", debit="4000.00", reference="RCPT-3"),
        _book(4, "2026-04-04", credit="5000.00", reference="PAY-9"),
    ]))


async def _create_group(stmt_ids, line_ids):
    return await bank_recon.create_bank_recon_group_match(
        object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        account_id=102, statement_line_ids=stmt_ids, line_ids=line_ids, created_by="tester",
    )


@pytest.mark.asyncio
async def test_create_group_match_writes_one_row_per_pair_with_shared_group(fake_bank_collections, monkeypatch):
    _group_fixture(fake_bank_collections, monkeypatch)

    out = await _create_group(["s1"], [1, 2])

    assert out["group_type"] == "one_to_many"
    assert out["amount"] == "15000.00"
    rows = fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows
    assert len(rows) == 2
    assert {r["match_group_id"] for r in rows} == {out["match_group_id"]}
    assert {r["statement_line_id"] for r in rows} == {"s1"}
    assert sorted(r["line_id"] for r in rows) == [1, 2]
    # Each row carries its own share, so the active rows sum to the group amount once.
    assert sum(Decimal(r["amount"]) for r in rows) == Decimal("15000.00")
    assert all(r["status"] == "active" and r["tenant_id"] == "tenant-a" for r in rows)
    assert all(r["group_amount"] == "15000.00" and r["group_size"] == 3 for r in rows)


@pytest.mark.asyncio
async def test_create_group_match_rejects_bad_groups(fake_bank_collections, monkeypatch):
    _group_fixture(fake_bank_collections, monkeypatch)

    with pytest.raises(AccountingValidationError, match="Totals do not agree"):
        await _create_group(["s1"], [1, 3])
    with pytest.raises(AccountingValidationError, match="same direction"):
        await _create_group(["s1"], [1, 4])
    with pytest.raises(AccountingValidationError, match="Statement line not found: s-other"):
        await _create_group(["s-other"], [1, 2])
    with pytest.raises(AccountingValidationError, match="Book entry not found"):
        await _create_group(["s1"], [1, 99])
    with pytest.raises(AccountingValidationError, match="Duplicate"):
        await _create_group(["s1"], [1, 1])
    with pytest.raises(AccountingValidationError, match="single match"):
        await _create_group(["s1"], [1])
    assert fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows == []

    await _create_group(["s1"], [1, 2])
    with pytest.raises(AccountingValidationError, match="statement line is already matched"):
        await _create_group(["s1"], [3, 2])
    # A book line inside a group also blocks a plain 1:1 match.
    with pytest.raises(AccountingValidationError, match="already matched"):
        await bank_recon.create_bank_recon_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="s2", line_id=2, created_by="tester",
        )


@pytest.mark.asyncio
async def test_reversing_one_row_reverses_the_whole_group(fake_bank_collections, monkeypatch):
    _group_fixture(fake_bank_collections, monkeypatch, matches=[
        {**_scope("tenant-b"), "match_id": "x1", "match_group_id": "SAME", "status": "active"},
    ])
    out = await _create_group(["s1"], [1, 2])
    first_match_id = out["matches"][0]["match_id"]

    result = await bank_recon.reverse_bank_recon_match(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        match_id=first_match_id, reversed_by="tester",
    )

    assert result["reversed_rows"] == 2
    assert result["match_group_id"] == out["match_group_id"]
    rows = fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows
    group_rows = [r for r in rows if r.get("match_group_id") == out["match_group_id"]]
    assert all(r["status"] == "reversed" and r["reversed_by"] == "tester" for r in group_rows)
    # Another tenant's row is untouched.
    assert next(r for r in rows if r["match_id"] == "x1")["status"] == "active"
    # Lines are free again.
    await _create_group(["s1"], [1, 2])


@pytest.mark.asyncio
async def test_build_bank_reconciliation_returns_group_suggestions(fake_bank_collections, monkeypatch):
    _group_fixture(fake_bank_collections, monkeypatch)

    out = await bank_recon.build_bank_reconciliation(
        object(), tenant_id="tenant-a", app_key="mitrabooks",
        accounting_entity_id="primary", account_id=102, as_of=date(2026, 4, 30),
    )

    assert out["suggestions"] == []
    assert len(out["group_suggestions"]) == 1
    g = out["group_suggestions"][0]
    assert g["statement_line_ids"] == ["s1"]
    assert sorted(g["line_ids"]) == [1, 2]

    await _create_group(["s1"], [1, 2])
    out = await bank_recon.build_bank_reconciliation(
        object(), tenant_id="tenant-a", app_key="mitrabooks",
        accounting_entity_id="primary", account_id=102, as_of=date(2026, 4, 30),
    )
    assert out["group_suggestions"] == []
    assert out["summary"]["matched_groups"] == 1
    assert [l["statement_line_id"] for l in out["in_bank_not_in_books"]] == ["s2"]
    assert sorted(l["line_id"] for l in out["in_books_not_in_bank"]) == [3, 4]


# ---- Match with a difference (bank charges / MDR / TDS / rounding) -------- #

def test_plan_difference_direction_for_each_case():
    # Customer paid 10,000; bank credited 9,990 (charges deducted) -> credit bank 10.
    p = plan_difference_adjustment([_stmt("s", "2026-04-05", deposit="9990.00")], [{"debit": "10000.00"}])
    assert (p["side"], p["bank_entry"], p["difference"], p["hint"]) == ("deposit", "credit", Decimal("10.00"), "bank_deducted")
    assert p["group_type"] == "one_to_one"
    # Paid 5,000; bank debited 5,017.70 (NEFT charge + GST) -> credit bank 17.70.
    p = plan_difference_adjustment([_stmt("s", "2026-04-05", withdrawal="5017.70")], [{"credit": "5000.00"}])
    assert (p["side"], p["bank_entry"], p["difference"], p["hint"]) == ("withdrawal", "credit", Decimal("17.70"), "bank_charged")
    # Bank credited more than booked -> debit bank.
    p = plan_difference_adjustment([_stmt("s", "2026-04-05", deposit="10000.50")], [{"debit": "10000.00"}])
    assert (p["bank_entry"], p["difference"], p["hint"]) == ("debit", Decimal("0.50"), "bank_excess")
    # Bank debited less than booked -> money still in the bank -> debit bank.
    p = plan_difference_adjustment([_stmt("s", "2026-04-05", withdrawal="4990.00")], [{"credit": "5000.00"}])
    assert (p["bank_entry"], p["difference"]) == ("debit", Decimal("10.00"))
    # Group: one deposit slip, two receipts, 50 short.
    p = plan_difference_adjustment(
        [_stmt("s", "2026-04-05", deposit="14950.00")], [{"debit": "10000.00"}, {"debit": "5000.00"}],
    )
    assert (p["group_type"], p["bank_entry"], p["difference"]) == ("one_to_many", "credit", Decimal("50.00"))


def test_plan_difference_rejects_invalid_selections():
    with pytest.raises(ValueError, match="already agree"):
        plan_difference_adjustment([_stmt("s", "2026-04-05", deposit="100.00")], [{"debit": "100.00"}])
    with pytest.raises(ValueError, match="not smaller"):
        plan_difference_adjustment([_stmt("s", "2026-04-05", deposit="100.00")], [{"debit": "300.00"}])
    with pytest.raises(ValueError, match="same direction"):
        plan_difference_adjustment([_stmt("s", "2026-04-05", deposit="100.00")], [{"credit": "99.00"}])
    with pytest.raises(ValueError, match="Many-to-many"):
        plan_difference_adjustment(
            [_stmt("a", "2026-04-05", deposit="100.00"), _stmt("b", "2026-04-05", deposit="1.00")],
            [{"debit": "50.00"}, {"debit": "50.00"}],
        )


def test_suggest_difference_matches_tolerance_and_preference():
    out = suggest_difference_matches(
        [
            _stmt("s-mdr", "2026-04-05", deposit="9764.00", desc="UPI SETTLEMENT"),    # 2.36% short of 10,000
            _stmt("s-big", "2026-04-05", deposit="900.00"),                            # 10% short of 1,000: too much
            _stmt("s-abs", "2026-04-05", withdrawal="201500.00"),                      # 1,500 over: above the cap
            _stmt("s-far", "2026-04-05", withdrawal="5017.70"),                        # book line 20 days away
        ],
        [
            _book(1, "2026-04-04", debit="10000.00"),
            _book(2, "2026-04-04", debit="9770.00"),   # closer amount wins for s-mdr
            _book(3, "2026-04-05", debit="1000.00"),
            _book(4, "2026-04-05", credit="200000.00"),
            _book(5, "2026-04-25", credit="5000.00"),
        ],
    )
    assert len(out) == 1
    g = out[0]
    assert (g["statement_line_id"], g["line_id"]) == ("s-mdr", 2)
    assert g["difference"] == "6.00" and g["bank_entry"] == "credit" and g["hint"] == "bank_deducted"
    assert g["statement_amount"] == "9764.00" and g["book_amount"] == "9770.00"
    # Exact matches are never offered as near-matches, and exclusions hold.
    assert suggest_difference_matches([_stmt("s", "2026-04-05", deposit="100.00")], [_book(1, "2026-04-05", debit="100.00")]) == []
    assert suggest_difference_matches(
        [_stmt("s", "2026-04-05", deposit="99.00")], [_book(1, "2026-04-05", debit="100.00")], exclude_line_ids={"1"},
    ) == []


class _FakeVoucherBook:
    """Stand-in for typed vouchers + the bank ledger: approving a voucher
    posts a journal line on the bank account (account 102)."""

    def __init__(self, fake_bank_collections, ledger):
        self.collections = fake_bank_collections
        self.ledger = ledger
        self.posted_payloads = []
        self.next_journal = 9000

    @property
    def vouchers(self):
        return self.collections.setdefault("business_vouchers", _FakeCollection())

    async def post(self, session, *, tenant_id, app_key, created_by, payload, idempotency_key):
        existing = await self.vouchers.find_one({"idempotency_key": idempotency_key})
        if existing:
            return dict(existing)
        self.posted_payloads.append(payload)
        doc = {
            "tenant_id": tenant_id, "app_key": app_key, "accounting_entity_id": payload.accounting_entity_id,
            "voucher_id": f"v-{len(self.posted_payloads)}", "status": "pending_approval",
            "idempotency_key": idempotency_key, "amount": str(payload.amount),
            "debit_account_id": payload.debit_account_id, "credit_account_id": payload.credit_account_id,
            "entry_date": payload.entry_date.isoformat(),
        }
        await self.vouchers.insert_one(doc)
        return dict(doc)

    async def approve(self, voucher_id):
        doc = await self.vouchers.find_one({"voucher_id": voucher_id})
        self.next_journal += 1
        doc.update({"status": "posted", "journal_entry_id": self.next_journal})
        amount = doc["amount"]
        self.ledger.append(_book(
            self.next_journal, doc["entry_date"],
            debit=amount if doc["debit_account_id"] == 102 else "0.00",
            credit=amount if doc["credit_account_id"] == 102 else "0.00",
            reference="BRDIFF",
        ) | {"journal_id": self.next_journal})
        return dict(doc)

    async def review(self, session, *, tenant_id, app_key, voucher_id, reviewed_by, payload):
        return await self.approve(voucher_id)


def _difference_fixture(fake_bank_collections, monkeypatch):
    fake_bank_collections[BANK_STATEMENT_LINES_COLLECTION] = _FakeCollection([
        {**_scope(), "account_id": 102, "statement_line_id": "s1", "txn_date": "2026-04-05",
         "description": "NEFT ACME LESS CHGS", "ref": "", "withdrawal": "0.00", "deposit": "9990.00", "balance": "9990.00"},
    ])
    fake_bank_collections[BANK_RECON_MATCHES_COLLECTION] = _FakeCollection()
    ledger = [_book(1, "2026-04-04", debit="10000.00", reference="RCPT-ACME")]
    monkeypatch.setattr("app.accounting.service.get_ledger_lines", _ledger_service(ledger))
    book = _FakeVoucherBook(fake_bank_collections, ledger)
    monkeypatch.setattr("app.modules.business.service.post_typed_voucher", book.post)
    monkeypatch.setattr("app.modules.business.service.review_typed_voucher", book.review)
    return book


async def _create_difference(approve, **overrides):
    kwargs = dict(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary", account_id=102,
        statement_line_ids=["s1"], line_ids=[1], offset_account_id=51001, offset_account_code=None,
        description=None, approve=approve, created_by="tester", idempotency_key=None,
    )
    kwargs.update(overrides)
    return await bank_recon.create_bank_recon_difference_match(object(), **kwargs)


async def _build():
    return await bank_recon.build_bank_reconciliation(
        object(), tenant_id="tenant-a", app_key="mitrabooks",
        accounting_entity_id="primary", account_id=102, as_of=date(2026, 4, 30),
    )


@pytest.mark.asyncio
async def test_difference_match_suggested_then_approved_immediately_reconciles(fake_bank_collections, monkeypatch):
    book = _difference_fixture(fake_bank_collections, monkeypatch)

    before = await _build()
    assert before["suggestions"] == [] and before["group_suggestions"] == []
    assert [(g["statement_line_id"], g["line_id"], g["difference"]) for g in before["difference_suggestions"]] == [("s1", 1, "10.00")]
    assert before["summary"]["difference"] == "0.00"  # identity holds; the gap shows as reconciling items

    out = await _create_difference(approve=True)

    payload = book.posted_payloads[0]
    assert payload.voucher_type == "journal"
    assert payload.amount == Decimal("10.00")
    assert payload.debit_account_id == 51001 and payload.credit_account_id == 102   # Dr Bank Charges, Cr Bank
    assert payload.entry_date.isoformat() == "2026-04-05"
    assert out["status"] == "active"
    rows = fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows
    assert {r["status"] for r in rows} == {"active"}
    assert len(rows) == 2
    adjustment = next(r for r in rows if r.get("is_adjustment"))
    assert adjustment["side"] == "withdrawal" and adjustment["amount"] == "10.00"
    assert adjustment["line_id"] == 9001

    after = await _build()
    assert after["summary"]["book_balance"] == "9990.00"
    assert after["summary"]["difference"] == "0.00"
    assert after["in_bank_not_in_books"] == [] and after["in_books_not_in_bank"] == []
    assert after["difference_suggestions"] == [] and after["pending_differences"] == []
    assert after["summary"]["matched_groups"] == 1


@pytest.mark.asyncio
async def test_difference_match_waits_for_approval_then_completes(fake_bank_collections, monkeypatch):
    book = _difference_fixture(fake_bank_collections, monkeypatch)

    out = await _create_difference(approve=False)
    assert out["status"] == "pending_adjustment"
    group_id = out["match_group_id"]

    pending = await _build()
    # Truthful BRS: still unmatched, but not suggested again and listed as pending.
    assert [l["statement_line_id"] for l in pending["in_bank_not_in_books"]] == ["s1"]
    assert pending["difference_suggestions"] == [] and pending["suggestions"] == []
    assert [(p["match_group_id"], p["difference"], p["statement_line_ids"], p["line_ids"]) for p in pending["pending_differences"]] == [
        (group_id, "10.00", ["s1"], [1]),
    ]
    # The held lines cannot be matched elsewhere meanwhile.
    with pytest.raises(AccountingValidationError, match="already matched"):
        await bank_recon.create_bank_recon_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            account_id=102, statement_line_id="s1", line_id=1, created_by="tester",
        )
    with pytest.raises(AccountingValidationError, match="waiting for approval"):
        await bank_recon.finalize_bank_recon_difference_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            match_group_id=group_id, finalized_by="tester",
        )

    await book.approve(out["voucher"]["voucher_id"])
    done = await bank_recon.finalize_bank_recon_difference_match(
        object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        match_group_id=group_id, finalized_by="approver",
    )
    assert done["status"] == "active" and len(done["matches"]) == 2
    after = await _build()
    assert after["summary"]["difference"] == "0.00"
    assert after["in_bank_not_in_books"] == [] and after["pending_differences"] == []
    with pytest.raises(AccountingValidationError, match="already complete"):
        await bank_recon.finalize_bank_recon_difference_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            match_group_id=group_id, finalized_by="approver",
        )


@pytest.mark.asyncio
async def test_difference_match_validation_and_unmatch(fake_bank_collections, monkeypatch):
    book = _difference_fixture(fake_bank_collections, monkeypatch)

    with pytest.raises(AccountingValidationError, match="Choose the account"):
        await _create_difference(approve=True, offset_account_id=None)
    assert book.posted_payloads == []  # nothing posted for a rejected request

    out = await _create_difference(approve=False)
    with pytest.raises(AccountingValidationError, match="already matched"):
        await _create_difference(approve=False)

    pending_row = fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows[0]
    result = await bank_recon.reverse_bank_recon_match(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        match_id=pending_row["match_id"], reversed_by="tester",
    )
    assert result["reversed_rows"] == 1
    assert result["adjustment_voucher_id"] == out["voucher"]["voucher_id"]
    assert "not reversed" in result["note"]
    # Lines are free again and suggested again.
    again = await _build()
    assert [g["statement_line_id"] for g in again["difference_suggestions"]] == ["s1"]


@pytest.mark.asyncio
async def test_difference_match_retry_after_rejected_voucher_posts_a_fresh_one(fake_bank_collections, monkeypatch):
    book = _difference_fixture(fake_bank_collections, monkeypatch)
    out = await _create_difference(approve=False)
    rejected = await book.vouchers.find_one({"voucher_id": out["voucher"]["voucher_id"]})
    rejected["status"] = "rejected"
    with pytest.raises(AccountingValidationError, match="rejected"):
        await bank_recon.finalize_bank_recon_difference_match(
            object(), tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
            match_group_id=out["match_group_id"], finalized_by="tester",
        )
    row = fake_bank_collections[BANK_RECON_MATCHES_COLLECTION].rows[0]
    await bank_recon.reverse_bank_recon_match(
        tenant_id="tenant-a", app_key="mitrabooks", accounting_entity_id="primary",
        match_id=row["match_id"], reversed_by="tester",
    )

    retry = await _create_difference(approve=True)

    assert retry["status"] == "active"
    assert retry["adjustment_voucher_id"] != out["voucher"]["voucher_id"]
    assert len(book.posted_payloads) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("role,expected_approve", [
    ("tenant_admin", True),
    ("super_admin", True),
    ("accountant", False),
    ("operator", False),
    (None, False),
])
async def test_difference_route_only_lets_voucher_approvers_approve(monkeypatch, role, expected_approve):
    from app.modules.business.routes import bank_recon_routes
    from app.modules.business.schemas import BankReconDifferenceMatchRequest

    seen = {}

    async def fake_create(session, **kwargs):
        seen.update(kwargs)
        return {"status": "active" if kwargs["approve"] else "pending_adjustment"}

    monkeypatch.setattr(bank_recon_routes.bank_recon, "create_bank_recon_difference_match", fake_create)
    monkeypatch.setattr(
        bank_recon_routes, "resolve_business_app_tenant",
        lambda **kwargs: SimpleNamespace(tenant_id="tenant-a", app_key="mitrabooks"),
    )

    out = await bank_recon_routes.business_bank_recon_match_difference(
        payload=BankReconDifferenceMatchRequest(
            account_id=102, statement_line_ids=["s1"], line_ids=[1], offset_account_id=51001, approve=True,
        ),
        accounting_entity_id="primary",
        _module_context={},
        session=object(),
        current_user={"role": role, "sub": "u1", "email": "u1@example.com"},
        x_tenant_id=None,
        x_app_key=None,
        x_idempotency_key=None,
    )

    assert seen["approve"] is expected_approve
    if not expected_approve:
        assert out["status"] == "pending_adjustment"
        assert "tenant admin" in out["note"]


@pytest.mark.asyncio
@pytest.mark.parametrize("role,expected_approve", [
    ("tenant_admin", True),
    ("super_admin", True),
    ("accountant", False),
    ("operator", False),
    (None, False),
])
async def test_statement_voucher_route_only_lets_voucher_approvers_approve(monkeypatch, role, expected_approve):
    from app.modules.business.routes import bank_recon_routes
    from app.modules.business.schemas import BankStatementVoucherRequest

    seen = {}

    async def fake_post(session, **kwargs):
        seen.update(kwargs)
        status = "posted" if kwargs["approve"] else "pending_approval"
        return {"statement_line_id": kwargs["statement_line_id"], "posting_status": status, "voucher": {}}

    monkeypatch.setattr(bank_recon_routes.bank_recon, "post_bank_statement_line_voucher", fake_post)
    monkeypatch.setattr(
        bank_recon_routes, "resolve_business_app_tenant",
        lambda **kwargs: SimpleNamespace(tenant_id="tenant-a", app_key="mitrabooks"),
    )

    out = await bank_recon_routes.business_bank_recon_statement_voucher(
        payload=BankStatementVoucherRequest(
            statement_line_id="stmt-charge", account_id=102, offset_account_id=51001, approve=True,
        ),
        _module_context={},
        session=object(),
        current_user={"role": role, "sub": "u1", "email": "u1@example.com"},
        x_tenant_id=None,
        x_app_key=None,
        x_idempotency_key=None,
    )

    assert seen["approve"] is expected_approve
    if expected_approve:
        assert "note" not in out
    else:
        assert out["posting_status"] == "pending_approval"
        assert "tenant admin" in out["note"]
