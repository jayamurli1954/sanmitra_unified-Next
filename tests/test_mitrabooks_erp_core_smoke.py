from datetime import date
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

import app.accounting.router as accounting_router
import app.core.auth.dependencies as auth_dependencies
import app.core.auth.router as auth_router
import app.core.modules.dependencies as module_dependencies
import app.core.modules.router as modules_router
import app.modules.business.service as business_service
from app.main import app
from app.modules.business import router as business_router


TENANT_ID = "tenant-mitrabooks-smoke"
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
                return

    async def delete_one(self, filters):
        self.docs = [doc for doc in self.docs if not self._matches(doc, filters)]

    @staticmethod
    def _matches(doc, filters):
        return all(doc.get(key) == value for key, value in filters.items())


def _default_tenant(*, enabled_modules: list[str] | None = None) -> dict:
    return {
        "tenant_id": TENANT_ID,
        "organization_type": "BUSINESS",
        "enabled_modules": enabled_modules or ["business", "accounting", "gst", "inventory", "audit"],
        "subscription_plan": "pro",
        "status": "active",
    }


def _default_current_user() -> dict:
    return {
        "sub": "business-smoke-user",
        "email": "business.admin@sanmitra.local",
        "tenant_id": TENANT_ID,
        "app_key": APP_KEY,
        "role": "tenant_admin",
    }


def _fake_business_collections() -> dict[str, FakeCollection]:
    return {
        business_service.PARTIES_COLLECTION: FakeCollection(),
        business_service.VOUCHERS_COLLECTION: FakeCollection(),
        business_service.VOUCHER_COUNTERS_COLLECTION: FakeCollection(),
    }


def _clear_dependency_overrides() -> None:
    app.dependency_overrides.pop(auth_dependencies.get_current_user, None)
    app.dependency_overrides.pop(accounting_router.get_async_session, None)
    app.dependency_overrides.pop(business_router.get_async_session, None)


def _install_smoke_context(
    *,
    async_session,
    monkeypatch,
    tenant: dict | None = None,
    current_user: dict | None = None,
    collections: dict[str, FakeCollection] | None = None,
) -> tuple[dict, dict, dict[str, FakeCollection]]:
    active_tenant = tenant or _default_tenant()
    active_user = current_user or _default_current_user()
    active_collections = collections or _fake_business_collections()

    async def fake_get_tenant(tenant_id: str):
        assert tenant_id == TENANT_ID
        return active_tenant

    async def fake_get_current_user():
        return active_user

    async def fake_session():
        yield async_session

    async def fake_login_user(email: str, password: str, *, app_key: str):
        assert email == "business.admin@sanmitra.local"
        assert password == "superadmin123"
        assert app_key == APP_KEY
        return "smoke-access-token", "smoke-refresh-token"

    async def noop_login_activity(**_kwargs):
        return None

    async def noop_audit_event(**_kwargs):
        return None

    monkeypatch.setattr(modules_router, "get_tenant", fake_get_tenant)
    monkeypatch.setattr(module_dependencies, "get_tenant", fake_get_tenant)
    monkeypatch.setattr(accounting_router, "get_tenant", fake_get_tenant)
    monkeypatch.setattr(auth_router, "login_user", fake_login_user)
    monkeypatch.setattr(auth_router, "_log_login_activity", noop_login_activity)
    monkeypatch.setattr(business_service, "get_collection", lambda name: active_collections[name])
    monkeypatch.setattr(business_service, "log_audit_event", noop_audit_event)

    app.dependency_overrides[auth_dependencies.get_current_user] = fake_get_current_user
    app.dependency_overrides[accounting_router.get_async_session] = fake_session
    app.dependency_overrides[business_router.get_async_session] = fake_session

    return active_tenant, active_user, active_collections


async def _initialize_accounts(client: AsyncClient, headers: dict) -> tuple[dict, dict]:
    init_response = await client.post("/api/v1/accounting/initialize-chart-of-accounts", headers=headers)
    assert init_response.status_code == 200

    accounts_response = await client.get("/api/v1/accounting/accounts", headers=headers)
    assert accounts_response.status_code == 200
    accounts = accounts_response.json()
    debit_account = next(account for account in accounts if account["type"] == "asset")
    credit_account = next(account for account in accounts if account["type"] in {"income", "liability"})
    return debit_account, credit_account


@pytest.mark.asyncio
async def test_mitrabooks_erp_core_smoke_login_modules_accounts_party_voucher_reversal_drilldown(
    async_session,
    monkeypatch,
):
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch)

    headers = {"X-App-Key": APP_KEY}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": "business.admin@sanmitra.local", "password": "superadmin123"},
                headers=headers,
            )
            assert login_response.status_code == 200
            assert login_response.json()["access_token"] == "smoke-access-token"

            module_response = await client.get("/api/v1/modules/me", headers=headers)
            assert module_response.status_code == 200
            module_payload = module_response.json()
            assert module_payload["organization_type"] == "BUSINESS"
            assert {item["module_key"] for item in module_payload["enabled_modules"]} >= {
                "accounting",
                "audit",
                "business",
            }

            init_response = await client.post("/api/v1/accounting/initialize-chart-of-accounts", headers=headers)
            assert init_response.status_code == 200
            assert init_response.json()["total_accounts"] >= 2

            accounts_response = await client.get("/api/v1/accounting/accounts", headers=headers)
            assert accounts_response.status_code == 200
            accounts = accounts_response.json()
            assert len(accounts) >= 2
            debit_account = next(account for account in accounts if account["type"] == "asset")
            credit_account = next(account for account in accounts if account["type"] in {"income", "liability"})

            party_response = await client.post(
                "/api/v1/business/parties",
                json={
                    "party_name": f"Smoke Customer {uuid4().hex[:8]}",
                    "party_type": "customer",
                    "party_code": f"SMK-{uuid4().hex[:8].upper()}",
                    "opening_balance": "0.00",
                },
                headers=headers,
            )
            assert party_response.status_code == 200
            party = party_response.json()
            assert party["tenant_id"] == TENANT_ID
            assert party["app_key"] == APP_KEY

            party_list_response = await client.get("/api/v1/business/parties", headers=headers)
            assert party_list_response.status_code == 200
            assert any(item["party_id"] == party["party_id"] for item in party_list_response.json()["items"])

            voucher_response = await client.post(
                "/api/v1/business/vouchers",
                json={
                    "voucher_type": "journal",
                    "entry_date": "2026-06-01",
                    "amount": "125.00",
                    "debit_account_id": debit_account["id"],
                    "credit_account_id": credit_account["id"],
                    "description": "MitraBooks ERP core smoke voucher",
                    "party_id": party["party_id"],
                    "accounting_entity_id": ACCOUNTING_ENTITY_ID,
                },
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-voucher-001"},
            )
            assert voucher_response.status_code == 200
            voucher = voucher_response.json()
            assert voucher["status"] == "posted"
            assert voucher["journal_entry_id"]

            voucher_list_response = await client.get("/api/v1/business/vouchers", headers=headers)
            assert voucher_list_response.status_code == 200
            assert any(item["voucher_id"] == voucher["voucher_id"] for item in voucher_list_response.json()["items"])

            voucher_detail_response = await client.get(f"/api/v1/business/vouchers/{voucher['voucher_id']}", headers=headers)
            assert voucher_detail_response.status_code == 200
            assert voucher_detail_response.json()["journal_entry_id"] == voucher["journal_entry_id"]

            drilldown_response = await client.get(
                "/api/v1/accounting/reports/drilldown",
                params={"from_date": "2026-06-01", "to_date": "2026-06-01", "level": "voucher"},
                headers=headers,
            )
            assert drilldown_response.status_code == 200
            assert any(item["id"] == voucher["journal_entry_id"] for item in drilldown_response.json()["items"])

            reverse_response = await client.post(
                f"/api/v1/business/vouchers/{voucher['voucher_id']}/reverse",
                json={"reversal_date": "2026-06-01", "reason": "MitraBooks ERP smoke reversal"},
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-reversal-001"},
            )
            assert reverse_response.status_code == 200
            reversed_voucher = reverse_response.json()
            assert reversed_voucher["status"] == "reversed"
            assert reversed_voucher["reversal_journal_entry_id"]

            original_detail_response = await client.get(
                f"/api/v1/accounting/reports/vouchers/{voucher['journal_entry_id']}",
                headers=headers,
            )
            assert original_detail_response.status_code == 200
            original_detail = original_detail_response.json()
            assert original_detail["reversed_by_journal_ids"] == [reversed_voucher["reversal_journal_entry_id"]]
            assert original_detail["total_debit"] == 125.0
            assert original_detail["total_credit"] == 125.0
            original_lines = {line["account_id"]: line for line in original_detail["lines"]}
            assert original_lines[debit_account["id"]]["debit"] == 125.0
            assert original_lines[debit_account["id"]]["credit"] == 0.0
            assert original_lines[credit_account["id"]]["debit"] == 0.0
            assert original_lines[credit_account["id"]]["credit"] == 125.0

            reversal_detail_response = await client.get(
                f"/api/v1/accounting/reports/vouchers/{reversed_voucher['reversal_journal_entry_id']}",
                headers=headers,
            )
            assert reversal_detail_response.status_code == 200
            reversal_detail = reversal_detail_response.json()
            assert reversal_detail["reversal_of_journal_id"] == voucher["journal_entry_id"]
            assert reversal_detail["total_debit"] == 125.0
            assert reversal_detail["total_credit"] == 125.0
            reversal_lines = {line["account_id"]: line for line in reversal_detail["lines"]}
            assert reversal_lines[debit_account["id"]]["debit"] == 0.0
            assert reversal_lines[debit_account["id"]]["credit"] == 125.0
            assert reversal_lines[credit_account["id"]]["debit"] == 125.0
            assert reversal_lines[credit_account["id"]]["credit"] == 0.0
    finally:
        _clear_dependency_overrides()


@pytest.mark.asyncio
async def test_mitrabooks_business_routes_reject_wrong_app_key_header(async_session, monkeypatch):
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/business/parties", headers={"X-App-Key": "mandirmitra"})

        assert response.status_code == 403
        assert response.json()["detail"] == "mitrabooks app context required"
    finally:
        _clear_dependency_overrides()


@pytest.mark.asyncio
async def test_mitrabooks_business_routes_fail_closed_when_business_module_disabled(async_session, monkeypatch):
    tenant = _default_tenant(enabled_modules=["accounting", "audit"])
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch, tenant=tenant)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/business/parties", headers={"X-App-Key": APP_KEY})

        assert response.status_code == 403
        assert "Module business is not enabled" in response.json()["detail"]
    finally:
        _clear_dependency_overrides()


@pytest.mark.asyncio
async def test_mitrabooks_voucher_posting_reuses_duplicate_idempotency_key(async_session, monkeypatch):
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch)
    headers = {"X-App-Key": APP_KEY}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            debit_account, credit_account = await _initialize_accounts(client, headers)
            payload = {
                "voucher_type": "journal",
                "entry_date": "2026-06-01",
                "amount": "50.00",
                "debit_account_id": debit_account["id"],
                "credit_account_id": credit_account["id"],
                "description": "Duplicate idempotency smoke voucher",
                "accounting_entity_id": ACCOUNTING_ENTITY_ID,
            }

            first = await client.post(
                "/api/v1/business/vouchers",
                json=payload,
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-duplicate-idem"},
            )
            second = await client.post(
                "/api/v1/business/vouchers",
                json=payload,
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-duplicate-idem"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["voucher_id"] == second.json()["voucher_id"]
        assert first.json()["created"] is True
        assert second.json()["created"] is False
    finally:
        _clear_dependency_overrides()


@pytest.mark.asyncio
async def test_mitrabooks_voucher_posting_resolves_account_codes(async_session, monkeypatch):
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch)
    headers = {"X-App-Key": APP_KEY}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            debit_account, credit_account = await _initialize_accounts(client, headers)
            response = await client.post(
                "/api/v1/business/vouchers",
                json={
                    "voucher_type": "receipt",
                    "entry_date": "2026-06-01",
                    "amount": "50.00",
                    "debit_account_code": debit_account["code"],
                    "credit_account_code": credit_account["code"],
                    "description": "Code resolved smoke voucher",
                    "accounting_entity_id": ACCOUNTING_ENTITY_ID,
                },
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-code-resolve"},
            )

        assert response.status_code == 200
        voucher = response.json()
        assert voucher["status"] == "posted"
        assert voucher["debit_account_id"] == debit_account["id"]
        assert voucher["credit_account_id"] == credit_account["id"]
    finally:
        _clear_dependency_overrides()


@pytest.mark.asyncio
async def test_mitrabooks_voucher_posting_initializes_default_accounts_for_codes(async_session, monkeypatch):
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch)
    headers = {"X-App-Key": APP_KEY}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/business/vouchers",
                json={
                    "voucher_type": "receipt",
                    "entry_date": "2026-06-01",
                    "amount": "50.00",
                    "debit_account_code": "11010",
                    "credit_account_code": "24001",
                    "description": "Code resolved smoke voucher without pre-initialized chart",
                    "accounting_entity_id": ACCOUNTING_ENTITY_ID,
                },
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-code-auto-chart"},
            )

            accounts_response = await client.get("/api/v1/accounting/accounts", headers=headers)

        assert response.status_code == 200
        voucher = response.json()
        assert voucher["status"] == "posted"
        assert accounts_response.status_code == 200
        codes = {account["code"] for account in accounts_response.json()}
        assert {"11010", "24001"}.issubset(codes)
    finally:
        _clear_dependency_overrides()


@pytest.mark.asyncio
async def test_mitrabooks_accounting_journal_rejects_unbalanced_posting(async_session, monkeypatch):
    _install_smoke_context(async_session=async_session, monkeypatch=monkeypatch)
    headers = {"X-App-Key": APP_KEY}

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            debit_account, credit_account = await _initialize_accounts(client, headers)
            response = await client.post(
                "/api/v1/accounting/journal",
                json={
                    "entry_date": "2026-06-01",
                    "description": "Unbalanced smoke journal",
                    "reference": "UNBALANCED-SMOKE",
                    "lines": [
                        {"account_id": debit_account["id"], "debit": "125.00", "credit": "0.00"},
                        {"account_id": credit_account["id"], "debit": "0.00", "credit": "124.00"},
                    ],
                },
                headers={**headers, "X-Idempotency-Key": "mitrabooks-smoke-unbalanced"},
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Debits and credits must be equal"
    finally:
        _clear_dependency_overrides()
