from datetime import datetime, timedelta, timezone

import pytest

from app.modules.legal_compat import retention


class _FakeCursor:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    async def to_list(self, length: int):
        return self.rows[:length]


class _FakeCollection:
    def __init__(self, rows: list[dict] | None = None):
        self.rows = rows or []
        self.find_query = None
        self.inserted = None

    def find(self, query: dict):
        self.find_query = query
        return _FakeCursor(self.rows)

    async def insert_one(self, doc: dict):
        self.inserted = doc


@pytest.mark.asyncio
async def test_chat_history_list_is_scoped_to_logged_in_user(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = _FakeCollection(
        [
            {
                "_id": "mongo-id",
                "record_id": "row-1",
                "user_id": "user-a",
                "query": "BNSS FIR quash checklist",
                "response": "Direct answer about quashing.",
                "strategy": "offline_bnss_fir_quashing_fallback",
                "retention_days": 30,
                "created_at": datetime(2026, 8, 16, tzinfo=timezone.utc),
                "expires_at": datetime(2026, 9, 15, tzinfo=timezone.utc),
            }
        ]
    )
    monkeypatch.setattr(retention, "get_collection", lambda name: collection)

    rows = await retention.list_legal_chat_history(
        tenant_id="tenant-1",
        app_key="legalmitra",
        user_id="user-a",
    )

    assert collection.find_query["tenant_id"] == "tenant-1"
    assert collection.find_query["app_key"] == "legalmitra"
    assert collection.find_query["user_id"] == "user-a"
    assert collection.find_query["expires_at"]["$gt"] <= datetime.now(timezone.utc)
    assert rows[0]["record_id"] == "row-1"
    assert rows[0]["title"] == "BNSS FIR quash checklist"
    assert rows[0]["query"] == "BNSS FIR quash checklist"
    assert "Direct answer" in rows[0]["preview"]
    assert rows[0]["created_at"].startswith("2026-08-16")


@pytest.mark.asyncio
async def test_chat_history_title_falls_back_when_query_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = _FakeCollection(
        [
            {
                "record_id": "row-blank",
                "user_id": "user-a",
                "query": "   ",
                "response": "## Quash FIR under BNSS\n\nPractice note follows.",
                "retention_days": 30,
                "created_at": datetime(2026, 8, 16, tzinfo=timezone.utc),
            }
        ]
    )
    monkeypatch.setattr(retention, "get_collection", lambda name: collection)

    rows = await retention.list_legal_chat_history(
        tenant_id="tenant-1",
        app_key="legalmitra",
        user_id="user-a",
    )

    assert rows[0]["title"] == "Quash FIR under BNSS"
    assert rows[0]["query"] == "Quash FIR under BNSS"


@pytest.mark.asyncio
async def test_upload_history_list_is_scoped_to_logged_in_user(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = _FakeCollection(
        [{"_id": "mongo-id", "upload_id": "upload-1", "user_id": "user-a", "stored_file_path": "hidden"}]
    )
    monkeypatch.setattr(retention, "get_collection", lambda name: collection)

    rows = await retention.list_legal_upload_records(
        tenant_id="tenant-1",
        app_key="legalmitra",
        user_id="user-a",
    )

    assert collection.find_query["tenant_id"] == "tenant-1"
    assert collection.find_query["app_key"] == "legalmitra"
    assert collection.find_query["user_id"] == "user-a"
    assert "stored_file_path" not in rows[0]


@pytest.mark.asyncio
async def test_saved_chat_history_sets_retention_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    collection = _FakeCollection()
    monkeypatch.setattr(retention, "get_collection", lambda name: collection)

    record_id = await retention.save_legal_chat_history(
        tenant_id="tenant-1",
        app_key="legalmitra",
        user_id="user-a",
        query="Section 138 NI Act limitation",
        query_type="advocate_research",
        response={"response": "answer", "provider": "gemini", "strategy": "hybrid", "citations": []},
        retention_days=30,
    )

    assert record_id
    assert collection.inserted["user_id"] == "user-a"
    assert collection.inserted["retention_days"] == 30
    assert collection.inserted["expires_at"] > datetime.now(timezone.utc) + timedelta(days=29)
