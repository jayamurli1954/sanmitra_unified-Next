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
    statement_line_dedupe_key,
    suggest_matches,
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
