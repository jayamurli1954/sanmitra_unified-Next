from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

import app.modules.mandir_compat.router as mandir_router
import app.core.modules.dependencies as module_deps
from app.core.auth.dependencies import get_current_user
from app.main import app


class FakeObjectId:
    pass


class FakeCursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, _field, _direction):
        return self

    def skip(self, value):
        self.docs = self.docs[value:]
        return self

    def limit(self, value):
        self.docs = self.docs[:value]
        return self

    async def to_list(self, length=None):
        if length is None:
            return list(self.docs)
        return list(self.docs)[:length]


class FakeDevoteeCollection:
    def __init__(self):
        self.docs: list[dict] = []

    def find(self, query):
        def matches(doc):
            return all(doc.get(k) == v for k, v in query.items())

        return FakeCursor([doc for doc in self.docs if matches(doc)])

    async def insert_one(self, doc):
        # Simulate Mongo assigning a non-JSON-serializable ObjectId to inserted docs.
        doc["_id"] = FakeObjectId()
        self.docs.append(dict(doc))
        return SimpleNamespace(inserted_id=doc["_id"])


@pytest.fixture()
def mandir_client(monkeypatch):
    collection = FakeDevoteeCollection()
    empty_collections = {
        "mandir_donations": FakeDevoteeCollection(),
        "mandir_seva_bookings": FakeDevoteeCollection(),
    }
    collection.related = empty_collections

    def fake_get_collection(name: str):
        if name == "mandir_devotees":
            return collection
        if name in empty_collections:
            return empty_collections[name]
        raise AssertionError(f"Unexpected collection: {name}")

    async def fake_get_tenant(tenant_id: str):
        return {
            "tenant_id": tenant_id,
            "organization_type": "TEMPLE",
            "enabled_modules": ["temple", "audit", "business"],
        }

    monkeypatch.setattr(mandir_router, "get_collection", fake_get_collection)
    monkeypatch.setattr(module_deps, "get_tenant", fake_get_tenant)
    app.dependency_overrides[get_current_user] = lambda: {
        "tenant_id": "tenant-1",
        "role": "tenant_admin",
        "app_key": "mandirmitra",
    }

    with TestClient(app) as client:
        yield client, collection

    app.dependency_overrides.pop(get_current_user, None)


def test_create_devotee_response_omits_mongo_internal_id(mandir_client):
    client, collection = mandir_client

    response = client.post(
        "/api/v1/devotees/",
        json={
            "first_name": "Raghavan",
            "last_name": "Iyer",
            "phone": "9876543210",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "pincode": "600004",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["first_name"] == "Raghavan"
    assert "_id" not in payload
    assert len(collection.docs) == 1
    assert "_id" in collection.docs[0]


def test_list_devotees_response_omits_mongo_internal_id(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "dev-1",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "name": "Sri Raghavan Iyer",
            "phone": "9876543210",
        }
    )

    response = client.get("/api/v1/devotees/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "dev-1"
    assert "_id" not in payload[0]


def test_search_devotees_response_omits_mongo_internal_id(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "dev-2",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "name": "Sri Raghavan Iyer",
            "phone": "9876543210",
        }
    )

    response = client.get("/api/v1/devotees/search/by-mobile/9876543210")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "dev-2"
    assert "_id" not in payload[0]


def test_search_devotees_does_not_cross_tenant_scope(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "tenant-2-devotee",
            "tenant_id": "tenant-2",
            "app_key": "mandirmitra",
            "name": "Tenant Two Devotee",
            "phone": "9876512340",
        }
    )

    response = client.get("/api/v1/devotees/search/by-mobile/9876512340")

    assert response.status_code == 200
    assert response.json() == []


def test_search_devotees_does_not_cross_temple_scope(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "temple-2-devotee",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "temple_id": 2,
            "name": "Temple Two Devotee",
            "phone": "9876512340",
        }
    )

    response = client.get(
        "/api/v1/devotees/search/by-mobile/9876512340",
        headers={"X-Temple-Id": "1"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_search_devotees_matches_selected_temple_scope(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "temple-1-devotee",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "temple_id": 1,
            "name": "Temple One Devotee",
            "phone": "9876512340",
        }
    )

    response = client.get(
        "/api/v1/devotees/search/by-mobile/9876512340",
        headers={"X-Temple-Id": "1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "temple-1-devotee"


def test_search_devotees_matches_legacy_same_tenant_when_temple_id_missing(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "legacy-devotee",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "name": "Legacy Devotee",
            "phone": "9876512340",
        }
    )

    response = client.get(
        "/api/v1/devotees/search/by-mobile/9876512340",
        headers={"X-Temple-Id": "1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == "legacy-devotee"
    assert payload[0]["temple_id"] == 1


def test_search_devotees_matches_legacy_donation_for_selected_temple(mandir_client):
    client, collection = mandir_client
    collection.related["mandir_donations"].docs.append(
        {
            "_id": FakeObjectId(),
            "id": "donation-1",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "devotee_phone": "9876512340",
            "devotee_name": "Raghavan Iyer",
            "devotee_email": "raghavan.iyer01@gmail.com",
        }
    )

    response = client.get(
        "/api/v1/devotees/search/by-mobile/9876512340",
        headers={"X-Temple-Id": "1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["source"] == "donation"
    assert payload[0]["temple_id"] == 1
    assert payload[0]["name"] == "Raghavan Iyer"


def test_search_devotees_does_not_match_legacy_other_tenant(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "tenant-2-legacy-devotee",
            "tenant_id": "tenant-2",
            "app_key": "mandirmitra",
            "name": "Tenant Two Legacy Devotee",
            "phone": "9876512340",
        }
    )

    response = client.get(
        "/api/v1/devotees/search/by-mobile/9876512340",
        headers={"X-Temple-Id": "1"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_pincode_lookup_returns_found_for_autofill(mandir_client, monkeypatch):
    client, _collection = mandir_client

    async def fake_lookup(_pincode):
        return "Chennai", "Tamil Nadu"

    monkeypatch.setattr(mandir_router, "_lookup_pincode_city_state", fake_lookup)

    response = client.get("/api/v1/pincode/lookup?pincode=600004")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pincode"] == "600004"
    assert payload["city"] == "Chennai"
    assert payload["state"] == "Tamil Nadu"
    assert payload["found"] is True


def test_pincode_lookup_returns_not_found_when_lookup_misses(mandir_client, monkeypatch):
    client, _collection = mandir_client

    async def fake_lookup(_pincode):
        return None, None

    monkeypatch.setattr(mandir_router, "_lookup_pincode_city_state", fake_lookup)

    response = client.get("/api/v1/pincode/lookup?pincode=999999")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pincode"] == "999999"
    assert payload["city"] is None
    assert payload["state"] is None
    assert payload["found"] is False


def test_pincode_lookup_uses_local_fallback_when_external_lookup_fails(mandir_client, monkeypatch):
    client, _collection = mandir_client

    async def fake_lookup(pincode):
        return mandir_router.MANDIR_PINCODE_FALLBACKS.get(pincode, (None, None))

    monkeypatch.setattr(mandir_router, "_lookup_pincode_city_state", fake_lookup)

    response = client.get("/api/v1/pincode/lookup?pincode=600004")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pincode"] == "600004"
    assert payload["city"] == "Chennai"
    assert payload["state"] == "Tamil Nadu"
    assert payload["found"] is True


def test_devotee_autofill_returns_found_payload(mandir_client):
    client, collection = mandir_client

    collection.docs.append(
        {
            "_id": FakeObjectId(),
            "id": "dev-3",
            "tenant_id": "tenant-1",
            "app_key": "mandirmitra",
            "name": "Smt. Lakshmi",
            "phone": "9998887776",
            "city": "Chennai",
        }
    )

    response = client.get("/api/v1/devotees/autofill/by-mobile/9998887776")

    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is True
    assert payload["phone"] == "9998887776"
    assert payload["devotee"]["id"] == "dev-3"
    assert "_id" not in payload["devotee"]


def test_devotee_autofill_returns_not_found_payload(mandir_client):
    client, _collection = mandir_client

    response = client.get("/api/v1/devotees/autofill/by-mobile/123")

    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is False
    assert payload["devotee"] is None
