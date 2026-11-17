"""SEC-01: the public guest-pass page must not leak gate passcodes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limiting import limiter
from app.modules.housing_compat import router as housing_router
from app.modules.housing_compat.routes import visitors_public  # noqa: F401  (registers routes)
from app.modules.housing_compat.visitor_pass import (
    pass_is_usable,
    verify_visitor_pass_token,
    visitor_pass_token,
)

VISITOR_ID = "6f1c2b9e-0d7a-4c8e-9a51-3b2f7d1e4c10"


class _Visitors:
    def __init__(self, docs):
        self.docs = {d["id"]: d for d in docs}

    async def find_one(self, query):
        return self.docs.get(query.get("id"))


def _doc(**overrides):
    doc = {
        "id": VISITOR_ID,
        "tenant_id": "tenant-a",
        "app_key": "gruhamitra",
        "visitor_name": "Ravi",
        "flat_number": "A-101",
        "passcode": "482913",
        "visitor_type": "guest",
        "status": "approved",
        "checked_out_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
    }
    doc.update(overrides)
    return doc


@pytest.fixture
def client(monkeypatch):
    def make(doc):
        monkeypatch.setattr(housing_router, "_visitors_collection", lambda: _Visitors([doc]))
        limiter.reset()
        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        app.include_router(housing_router.router)
        return TestClient(app)

    return make


def test_token_is_bound_to_visitor_and_expiry():
    expires = "2026-11-17T10:00:00+00:00"
    token = visitor_pass_token(VISITOR_ID, expires)
    assert len(token) == 32
    assert verify_visitor_pass_token(VISITOR_ID, expires, token)
    assert verify_visitor_pass_token(VISITOR_ID, expires, token.upper())
    assert not verify_visitor_pass_token(VISITOR_ID, "2026-11-18T10:00:00+00:00", token)
    assert not verify_visitor_pass_token("another-visitor", expires, token)
    assert not verify_visitor_pass_token(VISITOR_ID, expires, None)
    assert not verify_visitor_pass_token(VISITOR_ID, expires, "0" * 32)


def test_visitor_id_alone_no_longer_reveals_the_passcode(client):
    res = client(_doc()).get(f"/visitors/public/{VISITOR_ID}")
    assert res.status_code == 200
    body = res.json()
    assert body["passcode"] is None
    # The rest of the pass still renders (QR uses the id, guards verify by id).
    assert body["visitor_name"] == "Ravi" and body["id"] == VISITOR_ID
    assert res.headers["cache-control"] == "no-store, private"
    assert res.headers["referrer-policy"] == "no-referrer"


def test_tampered_token_does_not_reveal_the_passcode(client):
    doc = _doc()
    bad = visitor_pass_token(VISITOR_ID, "2030-01-01T00:00:00+00:00")
    res = client(doc).get(f"/visitors/public/{VISITOR_ID}", params={"t": bad})
    assert res.json()["passcode"] is None


def test_signed_share_link_shows_the_passcode(client):
    doc = _doc()
    token = visitor_pass_token(VISITOR_ID, doc["expires_at"])
    res = client(doc).get(f"/visitors/public/{VISITOR_ID}", params={"t": token})
    assert res.status_code == 200
    assert res.json()["passcode"] == "482913"


@pytest.mark.parametrize(
    "overrides",
    [
        {"expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()},
        {"status": "rejected"},
        {"checked_out_at": datetime.now(timezone.utc).isoformat()},
    ],
    ids=["expired", "rejected", "checked-out"],
)
def test_closed_passes_never_show_the_passcode_even_when_signed(client, overrides):
    doc = _doc(**overrides)
    token = visitor_pass_token(VISITOR_ID, doc["expires_at"])
    res = client(doc).get(f"/visitors/public/{VISITOR_ID}", params={"t": token})
    assert res.status_code == 200
    assert res.json()["passcode"] is None


def test_unknown_pass_is_404(client):
    res = client(_doc()).get("/visitors/public/does-not-exist")
    assert res.status_code == 404


def test_public_pass_is_rate_limited(client):
    http = client(_doc())
    codes = [http.get(f"/visitors/public/{VISITOR_ID}").status_code for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429


def test_pass_is_usable_flags():
    now = datetime(2026, 11, 17, 10, tzinfo=timezone.utc)
    later = "2026-11-17T12:00:00+00:00"
    assert pass_is_usable({"expires_at": later, "status": "approved"}, now=now) == (False, True)
    assert pass_is_usable({"expires_at": "2026-11-17T09:00:00+00:00"}, now=now) == (True, False)
    assert pass_is_usable({"status": "rejected"}, now=now) == (False, False)


def test_visitor_response_carries_the_share_token():
    row = _doc()
    data = housing_router._visitor_response(row)
    assert data["pass_token"] == visitor_pass_token(VISITOR_ID, row["expires_at"])


def test_new_passcodes_use_a_cryptographic_generator():
    import inspect

    from app.modules.housing_compat.routes import visitors

    source = inspect.getsource(visitors.visitors_create)
    assert "secrets.choice" in source
    assert "random.choices" not in source
