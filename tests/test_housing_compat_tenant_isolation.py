from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.modules.housing_compat import router as housing_router
from app.modules.housing_compat import service as housing_service
from app.modules.housing_compat.schemas import (
    ArrearsTransferRequest,
    CompleteResidentRegistrationRequest,
    DamageClaimCreate,
    PublicJoinRequestCreate,
    SocietySettingsUpdate,
)


class _AsyncCursor:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def sort(self, *_args, **_kwargs):
        return self

    async def to_list(self, length=None):
        return self.rows[:length] if length else self.rows


class _Collection:
    def __init__(self, name: str, rows: list[dict] | None = None):
        self.name = name
        self.rows = rows or []
        self.find_one_queries: list[dict] = []
        self.find_queries: list[dict] = []
        self.update_queries: list[dict] = []
        self.delete_queries: list[dict] = []
        self.inserted: list[dict] = []

    async def find_one(self, query, *args, **kwargs):
        self.find_one_queries.append(query)
        for row in self.rows:
            if _matches(row, query):
                return dict(row)
        return None

    def find(self, query, *args, **kwargs):
        self.find_queries.append(query)
        return _AsyncCursor([dict(row) for row in self.rows if _matches(row, query)])

    async def update_one(self, query, update, *args, **kwargs):
        self.update_queries.append(query)
        if kwargs.get("upsert") and not any(_matches(row, query) for row in self.rows):
            doc = dict(update.get("$setOnInsert") or {})
            doc.update(update.get("$set") or {})
            self.rows.append(doc)
        return type("Result", (), {"matched_count": 1})()

    async def delete_many(self, query):
        self.delete_queries.append(query)
        self.rows = [row for row in self.rows if not _matches(row, query)]
        return type("Result", (), {"deleted_count": 0})()

    async def count_documents(self, query):
        return sum(1 for row in self.rows if _matches(row, query))

    async def insert_one(self, doc):
        self.inserted.append(doc)
        self.rows.append(doc)
        return type("Result", (), {"inserted_id": "inserted"})()

    async def insert_many(self, docs):
        self.inserted.extend(docs)
        self.rows.extend(docs)
        return type("Result", (), {"inserted_ids": list(range(len(docs)))})()


class _SqlRows:
    def __init__(self, rows: list):
        self.rows = rows

    def all(self):
        return self.rows


class _ExpenseAccountSession:
    def __init__(self, account_rows: list[tuple[str, str]]):
        self.account_rows = account_rows
        self.calls = 0

    async def execute(self, _stmt):
        self.calls += 1
        if self.calls == 1:
            return _SqlRows([])
        return _SqlRows(self.account_rows)


def test_expense_period_matching_accepts_explicit_month_and_two_digit_year_narration():
    assert housing_router._matches_expense_period(
        {"expense_month": "April, 2026", "narration": "Posted on 26 May"},
        month=4,
        year=2026,
    )
    assert housing_router._matches_expense_period(
        {"narration": "Electricity charges paid for the month of April 26"},
        month=4,
        year=2026,
    )
    assert housing_router._matches_expense_period(
        {"description": "Salary paid to watchman for Apr. 26"},
        month=4,
        year=2026,
    )
    assert not housing_router._matches_expense_period(
        {"expense_month": "May, 2026", "narration": "Electricity charges paid for the month of May 26"},
        month=4,
        year=2026,
    )


@pytest.mark.asyncio
async def test_expense_accounts_classify_water_from_voucher_text_and_split_same_code(monkeypatch):
    txns = _Collection(
        "mb_transactions",
        rows=[
            {
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "voucher_type": "payment",
                "expense_month": "April, 2026",
                "voucher_number": "PV-000001",
                "narration": "being water supply charges paid to Ramanna for 25 tanker for the month of Ap",
                "lines": [{"account_code": "5090", "description": "Generic Expense", "debit": 15000}],
            },
            {
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "voucher_type": "payment",
                "expense_month": "April, 2026",
                "voucher_number": "PV-000002",
                "narration": "salary paid to watchman for Apr 26",
                "lines": [{"account_code": "5090", "description": "Generic Expense", "debit": 15000}],
            },
        ],
    )

    monkeypatch.setattr(housing_router, "get_collection", lambda name: txns)

    rows = await housing_router._expense_accounts_for_period(
        _ExpenseAccountSession([("5090", "Generic Expense")]),
        tenant_id="society-1",
        app_key="gruhamitra",
        month=4,
        year=2026,
    )

    water_rows = [row for row in rows if row["is_water"]]
    fixed_rows = [row for row in rows if not row["is_water"]]
    assert len(water_rows) == 1
    assert len(fixed_rows) == 1
    assert water_rows[0]["account_code"] == "5090"
    assert water_rows[0]["total_amount"] == 15000
    assert fixed_rows[0]["account_code"] == "5090"
    assert fixed_rows[0]["total_amount"] == 15000


@pytest.mark.asyncio
async def test_maintenance_generation_requires_active_members_before_replacing_bills(monkeypatch):
    bills = _Collection(
        "housing_maintenance_bills",
        rows=[
            {
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "month": 4,
                "year": 2026,
                "flat_number": "A-101",
            }
        ],
    )

    async def flats_without_members(**_kwargs):
        return [
            {"id": "flat-1", "flat_number": "A-101", "area_sqft": 1000},
            {"id": "flat-2", "flat_number": "A-102", "area_sqft": 1000},
        ]

    monkeypatch.setattr(housing_router, "list_flats", flats_without_members)

    async def no_occupants(**_kwargs):
        return {}

    monkeypatch.setattr(housing_router, "_flat_occupants_map", no_occupants)
    monkeypatch.setattr(housing_router, "_maintenance_collections", lambda: (bills, _Collection("reversals")))

    with pytest.raises(HTTPException) as exc_info:
        await housing_router._build_maintenance_bills(
            tenant_id="society-1",
            app_key="gruhamitra",
            payload={"month": 4, "year": 2026},
            current_user={"sub": "admin"},
            session=object(),
        )

    assert exc_info.value.status_code == 400
    assert "active onboarded members" in str(exc_info.value.detail)
    assert bills.delete_queries == []


@pytest.mark.asyncio
async def test_maintenance_generation_bills_only_member_assigned_flats(monkeypatch):
    bills = _Collection("housing_maintenance_bills")
    async def mixed_flats(**_kwargs):
        return [
            {"id": "flat-1", "flat_number": "A-101", "area_sqft": 1000},
            {"id": "flat-2", "flat_number": "A-102", "area_sqft": 1000},
        ]

    monkeypatch.setattr(housing_router, "list_flats", mixed_flats)

    async def one_occupied_flat(**_kwargs):
        return {"A-101": 3}

    async def no_expenses(*_args, **_kwargs):
        return []

    async def empty_settings(**_kwargs):
        return {}

    monkeypatch.setattr(housing_router, "_flat_occupants_map", one_occupied_flat)
    monkeypatch.setattr(housing_router, "_expense_accounts_for_period", no_expenses)
    monkeypatch.setattr(housing_router, "get_society_settings", empty_settings)
    monkeypatch.setattr(housing_router, "_maintenance_collections", lambda: (bills, _Collection("reversals")))

    result = await housing_router._build_maintenance_bills(
        tenant_id="society-1",
        app_key="gruhamitra",
        payload={"month": 4, "year": 2026, "override_sqft_rate": 2},
        current_user={"sub": "admin"},
        session=object(),
    )

    assert result["total_bills_generated"] == 1
    assert bills.inserted[0]["flat_number"] == "A-101"
    assert bills.inserted[0]["breakdown"]["inmates_used"] == 3


@pytest.mark.asyncio
async def test_maintenance_generation_uses_exact_water_rate_fixed_expenses_and_settings(monkeypatch):
    bills = _Collection("housing_maintenance_bills")
    flat_numbers = ["A-101", "A-102", "A-103", "A-201", "A-202", "A-203", "A-301", "A-302", "A-303"]
    occupants = {
        "A-101": 5,
        "A-102": 6,
        "A-103": 6,
        "A-201": 6,
        "A-202": 6,
        "A-203": 6,
        "A-301": 6,
        "A-302": 6,
        "A-303": 5,
    }

    async def nine_flats(**_kwargs):
        return [
            {"id": f"flat-{idx}", "flat_number": flat_number, "area_sqft": 1000}
            for idx, flat_number in enumerate(flat_numbers, start=1)
        ]

    async def occupant_counts(**_kwargs):
        return occupants

    async def period_expenses(*_args, **_kwargs):
        return [
            {"account_code": "5060", "account_name": "Water Supply Expense", "total_amount": 15000, "is_water": True},
            {"account_code": "5010", "account_name": "Electricity Expense", "total_amount": 7256, "is_water": False},
            {"account_code": "5020", "account_name": "Watchman Salary", "total_amount": 15000, "is_water": False},
        ]

    async def billing_settings(**_kwargs):
        return {
            "sinking_fund_rate": 100,
            "repair_fund_rate": 200,
            "association_fund_rate": 50,
            "corpus_fund_rate": 25,
        }

    monkeypatch.setattr(housing_router, "list_flats", nine_flats)
    monkeypatch.setattr(housing_router, "_flat_occupants_map", occupant_counts)
    monkeypatch.setattr(housing_router, "_expense_accounts_for_period", period_expenses)
    monkeypatch.setattr(housing_router, "get_society_settings", billing_settings)
    monkeypatch.setattr(housing_router, "_maintenance_collections", lambda: (bills, _Collection("reversals")))

    result = await housing_router._build_maintenance_bills(
        tenant_id="society-1",
        app_key="gruhamitra",
        payload={"month": 4, "year": 2026, "selected_fixed_expense_codes": []},
        current_user={"sub": "admin"},
        session=object(),
    )

    first_bill = bills.inserted[0]
    assert result["total_bills_generated"] == 9
    assert result["ledger_water_total"] == 15000
    assert result["selected_fixed_expenses_total"] == 22256
    assert first_bill["flat_number"] == "A-101"
    assert first_bill["water_amount"] == 1442.31
    assert first_bill["fixed_amount"] == 2472.89
    assert first_bill["sinking_fund_amount"] == 100
    assert first_bill["repair_fund_amount"] == 200
    assert first_bill["association_fund_amount"] == 50
    assert first_bill["corpus_fund_amount"] == 25
    assert first_bill["breakdown"]["total_inmates"] == 52
    assert first_bill["breakdown"]["water_per_person_rate"] == 288.4615


@pytest.mark.asyncio
async def test_maintenance_posting_rejects_bills_without_active_members(monkeypatch):
    bills = _Collection(
        "housing_maintenance_bills",
        rows=[
            {
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "id": "bill-1",
                "month": 4,
                "year": 2026,
                "flat_number": "A-101",
                "status": "generated",
                "is_posted": False,
                "amount": 1000,
            }
        ],
    )
    posted: list[dict] = []

    async def no_occupants(**_kwargs):
        return {}

    async def fake_post(**kwargs):
        posted.append(kwargs)
        return 1

    monkeypatch.setattr(
        housing_router,
        "resolve_gruha_tenant",
        lambda **_kwargs: type("TenantContext", (), {"tenant_id": "society-1", "app_key": "gruhamitra"})(),
    )
    monkeypatch.setattr(housing_router, "_maintenance_collections", lambda: (bills, _Collection("reversals")))
    monkeypatch.setattr(housing_router, "_flat_occupants_map", no_occupants)
    monkeypatch.setattr(housing_router, "_post_maintenance_bill_to_accounting", fake_post)

    with pytest.raises(HTTPException) as exc_info:
        await housing_router.maintenance_post_bills(
            {"month": 4, "year": 2026},
            session=object(),
            current_user={"sub": "admin"},
        )

    assert exc_info.value.status_code == 400
    assert "without active onboarded members" in str(exc_info.value.detail)
    assert posted == []
    assert bills.update_queries == []


@pytest.mark.asyncio
async def test_maintenance_bill_posts_total_to_member_dues_income(monkeypatch):
    captured: dict[str, object] = {}

    async def fake_account_ids(_session, *, tenant_id, app_key, codes):
        captured["tenant_id"] = tenant_id
        captured["app_key"] = app_key
        captured["codes"] = set(codes)
        return {"1100": 1, "4000": 2}

    async def fake_post_journal_entry(_session, **kwargs):
        captured["payload"] = kwargs["payload"]
        captured["idempotency_key"] = kwargs["idempotency_key"]
        return type("Entry", (), {"id": 99})(), True

    monkeypatch.setattr(housing_router, "_account_ids_by_code", fake_account_ids)
    monkeypatch.setattr(housing_router, "post_journal_entry", fake_post_journal_entry)

    journal_id = await housing_router._post_maintenance_bill_to_accounting(
        object(),
        tenant_id="society-1",
        app_key="gruhamitra",
        bill={
            "id": "bill-1",
            "flat_number": "A-101",
            "month": 4,
            "year": 2026,
            "amount": 5415.20,
            "fixed_amount": 2472.89,
            "water_amount": 1442.31,
            "sinking_fund_amount": 500,
            "repair_fund_amount": 500,
            "association_fund_amount": 500,
        },
        current_user={"sub": "admin-1"},
    )

    lines = captured["payload"].lines
    assert journal_id == 99
    assert captured["codes"] == {"1100", "4000"}
    assert lines[0].account_id == 1
    assert lines[0].debit == Decimal("5415.20")
    assert lines[0].credit == Decimal("0.00")
    assert lines[1].account_id == 2
    assert lines[1].debit == Decimal("0.00")
    assert lines[1].credit == Decimal("5415.20")
    assert captured["idempotency_key"] == "gruhamitra:society-1:gruhamitra:maintenance-bill:bill-1"


@pytest.mark.asyncio
async def test_society_settings_routes_use_gruhamitra_header_context(monkeypatch):
    calls: list[dict] = []

    async def fake_get_society_settings(**kwargs):
        calls.append({"op": "get", **kwargs})
        return {"tenant_id": kwargs["tenant_id"], "app_key": kwargs["app_key"], "blocks_config": []}

    async def fake_save_society_settings(**kwargs):
        calls.append({"op": "save", **kwargs})
        return {
            "tenant_id": kwargs["tenant_id"],
            "app_key": kwargs["app_key"],
            "blocks_config": [],
            "sinking_fund_rate": 100,
        }

    monkeypatch.setattr(housing_router, "get_society_settings", fake_get_society_settings)
    monkeypatch.setattr(housing_router, "save_society_settings", fake_save_society_settings)

    await housing_router.society_settings_get(
        current_user={"tenant_id": "default", "app_key": "mitrabooks", "role": "super_admin"},
        x_tenant_id="society-1",
        x_app_key="gruhamitra",
    )
    await housing_router.society_settings_patch(
        payload=SocietySettingsUpdate(sinking_fund_rate=100),
        current_user={"tenant_id": "default", "app_key": "mitrabooks", "role": "super_admin"},
        x_tenant_id="society-1",
        x_app_key="gruhamitra",
    )

    assert calls[0]["tenant_id"] == "society-1"
    assert calls[0]["app_key"] == "gruhamitra"
    assert calls[1]["tenant_id"] == "society-1"
    assert calls[1]["app_key"] == "gruhamitra"


def _matches(row: dict, query: dict) -> bool:
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(row, clause) for clause in expected):
                return False
            continue
        value = row.get(key)
        if isinstance(expected, dict):
            if "$exists" in expected:
                if (key in row) is not bool(expected["$exists"]):
                    return False
            if "$in" in expected and value not in expected["$in"]:
                return False
            if "$ne" in expected and value == expected["$ne"]:
                return False
        elif value != expected:
            return False
    return True


@pytest.mark.asyncio
async def test_society_settings_and_generated_flats_are_scoped_by_app_key(monkeypatch):
    settings = _Collection("housing_society_settings")
    flats = _Collection(
        "housing_flats",
        rows=[
            {"tenant_id": "society-1", "app_key": "other-app", "flat_number": "X-101"},
            {"tenant_id": "society-1", "app_key": "gruhamitra", "flat_number": "A-101"},
        ],
    )
    collections = {
        housing_service.SOCIETY_SETTINGS: settings,
        housing_service.FLATS: flats,
    }
    monkeypatch.setattr(housing_service, "get_collection", lambda name: collections[name])

    payload = SocietySettingsUpdate(blocks_config=[{"name": "B", "floors": 1, "flatsPerFloor": 1}])
    row = await housing_service.save_society_settings(tenant_id="society-1", app_key="gruhamitra", payload=payload)

    assert settings.find_one_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra"}
    assert settings.update_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra"}
    assert flats.delete_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra"}
    assert flats.inserted[0]["app_key"] == "gruhamitra"
    assert row["app_key"] == "gruhamitra"


@pytest.mark.asyncio
async def test_public_membership_paths_are_limited_to_gruhamitra_app_key(monkeypatch):
    now = datetime.now(timezone.utc)
    joins = _Collection(
        "housing_membership_requests",
        rows=[
            {
                "id": "m-other",
                "society_id": "society-1",
                "app_key": "other-app",
                "email": "resident@example.com",
                "full_name": "Other App Resident",
                "role": "resident",
                "status": "active",
                "unit_label": "X-101",
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    monkeypatch.setattr(housing_service, "get_collection", lambda name: joins)

    created = await housing_service.create_public_join_request(
        society_id="society-1",
        payload=PublicJoinRequestCreate(
            full_name="Gruha Resident",
            email="resident@example.com",
            mobile="9999999999",
        ),
    )
    assert joins.find_one_queries[0]["app_key"] == "gruhamitra"
    assert created["app_key"] == "gruhamitra"

    users: list[dict] = []

    async def fake_create_user(**kwargs):
        users.append(kwargs)

    joins.rows.append(
        {
            "id": "m-gruha",
            "society_id": "society-1",
            "app_key": "gruhamitra",
            "email": "resident@example.com",
            "full_name": "Gruha Resident",
            "role": "resident",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
    )
    monkeypatch.setattr(housing_service, "create_user", fake_create_user)

    result = await housing_service.complete_resident_registration(
        payload=CompleteResidentRegistrationRequest(
            email="resident@example.com",
            password="secret123",
            terms_accepted=True,
            privacy_accepted=True,
        )
    )

    assert joins.find_one_queries[-1] == {
        "email": "resident@example.com",
        "app_key": "gruhamitra",
        "status": "active",
    }
    assert users[0]["app_key"] == "gruhamitra"
    assert result["society_id"] == "society-1"


@pytest.mark.asyncio
async def test_join_request_profile_and_unit_reads_include_app_key(monkeypatch):
    now = datetime.now(timezone.utc)
    joins = _Collection(
        "housing_membership_requests",
        rows=[
            {
                "id": "m1",
                "society_id": "society-1",
                "app_key": "gruhamitra",
                "email": "resident@example.com",
                "full_name": "Resident",
                "role": "resident",
                "status": "pending",
                "unit_label": "A-101",
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": "m2",
                "society_id": "society-1",
                "app_key": "other-app",
                "email": "resident@example.com",
                "full_name": "Other Resident",
                "role": "resident",
                "status": "pending",
                "unit_label": "X-101",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    members = _Collection(
        "housing_members",
        rows=[
            {"tenant_id": "society-1", "app_key": "gruhamitra", "flat_number": "A-101"},
            {"tenant_id": "society-1", "app_key": "other-app", "flat_number": "X-101"},
        ],
    )
    collections = {
        housing_service.JOIN_REQUESTS: joins,
        housing_service.MEMBERS: members,
    }
    monkeypatch.setattr(housing_service, "get_collection", lambda name: collections[name])

    await housing_service.list_join_requests(society_id="society-1", app_key="gruhamitra", status="pending")
    await housing_service.list_my_memberships(email="resident@example.com", app_key="gruhamitra")
    units = await housing_service.list_society_units(society_id="society-1", app_key="gruhamitra")

    assert joins.find_queries[0] == {"society_id": "society-1", "app_key": "gruhamitra", "status": "pending"}
    assert joins.find_queries[1] == {"email": "resident@example.com", "app_key": "gruhamitra"}
    assert members.find_queries[0] == {
        "tenant_id": "society-1",
        "app_key": "gruhamitra",
        "flat_number": {"$exists": True},
    }
    assert joins.find_queries[2] == {
        "society_id": "society-1",
        "app_key": "gruhamitra",
        "unit_label": {"$exists": True},
    }
    assert units == [{"id": "society-1:A-101", "unit_label": "A-101"}]


@pytest.mark.asyncio
async def test_arrears_and_damage_claim_store_money_without_float(monkeypatch):
    members = _Collection(
        "housing_members",
        rows=[
            {
                "id": "member-1",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "flat_number": "A-101",
            }
        ],
    )
    arrears = _Collection("housing_personal_arrears")
    claims = _Collection("housing_damage_claims")
    collections = {
        housing_service.MEMBERS: members,
        housing_service.ARREARS: arrears,
        housing_service.DAMAGE_CLAIMS: claims,
    }
    monkeypatch.setattr(housing_service, "get_collection", lambda name: collections[name])

    arrears_doc = await housing_service.transfer_to_arrears(
        tenant_id="society-1",
        app_key="gruhamitra",
        payload=ArrearsTransferRequest(member_id="member-1", amount=Decimal("1234.50")),
    )
    claim_result = await housing_service.raise_damage_claim(
        tenant_id="society-1",
        app_key="gruhamitra",
        payload=DamageClaimCreate(flat_id="A-101", amount=Decimal("99.99"), description="Window damage"),
    )

    assert arrears_doc["original_balance"] == "1234.50"
    assert arrears_doc["current_balance"] == "1234.50"
    assert claims.inserted[0]["amount"] == "99.99"
    assert claim_result["total_amount"] == "99.99"


@pytest.mark.asyncio
async def test_router_branding_occupants_and_member_forms_include_app_key(monkeypatch):
    settings = _Collection(
        "housing_society_settings",
        rows=[{"tenant_id": "society-1", "app_key": "gruhamitra", "society_name": "Gruha Society"}],
    )
    documents = _Collection("housing_documents")
    members = _Collection(
        "housing_members",
        rows=[
            {
                "id": "tenant-1",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "Tenant",
                "flat_number": "A-101",
                "member_type": "tenant",
                "status": "active",
                "is_primary": True,
                "total_occupants": 3,
            },
            {
                "id": "owner-1",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "Owner",
                "flat_number": "A-101",
                "member_type": "owner",
                "status": "active",
            },
            {
                "id": "other-tenant",
                "tenant_id": "society-1",
                "app_key": "other-app",
                "name": "Other",
                "flat_number": "A-101",
                "member_type": "tenant",
                "status": "active",
                "is_primary": True,
                "total_occupants": 9,
            },
        ],
    )
    collections = {
        "housing_society_settings": settings,
        "housing_documents": documents,
        "housing_members": members,
    }
    monkeypatch.setattr(housing_router, "get_collection", lambda name: collections[name])
    monkeypatch.setattr(housing_router, "_build_simple_pdf", lambda *args, **kwargs: b"PDF")

    await housing_router._get_society_branding(tenant_id="society-1", app_key="gruhamitra")
    occupants = await housing_router._flat_occupants_map(tenant_id="society-1", app_key="gruhamitra")
    await housing_router.move_police_verification_form(
        member_id="tenant-1",
        current_user={"tenant_id": "society-1", "app_key": "gruhamitra", "role": "tenant_admin"},
        x_tenant_id=None,
    )
    await housing_router.move_tenant_id_form(
        member_id="tenant-1",
        current_user={"tenant_id": "society-1", "app_key": "gruhamitra", "role": "tenant_admin"},
        x_tenant_id=None,
    )

    assert settings.find_one_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra"}
    assert members.find_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra"}
    assert occupants == {"A-101": 3}
    assert members.find_one_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra", "id": "tenant-1"}
    assert members.find_one_queries[1]["app_key"] == "gruhamitra"
    assert members.find_one_queries[2] == {"tenant_id": "society-1", "app_key": "gruhamitra", "id": "tenant-1"}


@pytest.mark.asyncio
async def test_message_rooms_are_filtered_by_restricted_flat_audience(monkeypatch):
    rooms = _Collection(
        "housing_message_rooms",
        rows=[
            {
                "id": "general",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "General",
                "type": "general",
                "audience_type": "public",
            },
            {
                "id": "meeting-notices",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "Meeting Notices",
                "type": "meeting_notices",
                "audience_type": "public",
            },
            {
                "id": "mc-room",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "MC Members",
                "type": "meeting_notices",
                "audience_type": "flats",
                "allowed_flat_numbers": ["A-101"],
            },
            {
                "id": "other-room",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "Other Block",
                "type": "meeting_notices",
                "audience_type": "flats",
                "allowed_flat_numbers": ["B-201"],
            },
        ],
    )
    messages = _Collection("housing_messages")
    members = _Collection(
        "housing_members",
        rows=[
            {
                "id": "member-1",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "email": "resident@example.com",
                "flat_number": "A-101",
            }
        ],
    )
    collections = {
        "housing_message_rooms": rooms,
        "housing_messages": messages,
        "housing_members": members,
    }
    monkeypatch.setattr(housing_router, "get_collection", lambda name: collections[name])

    current_user = {
        "tenant_id": "society-1",
        "app_key": "gruhamitra",
        "role": "member",
        "email": "resident@example.com",
        "sub": "member-1",
    }
    visible = await housing_router.messages_list_rooms(current_user=current_user, x_tenant_id=None, x_app_key=None)

    assert {room["id"] for room in visible} == {"general", "meeting-notices", "mc-room"}
    with pytest.raises(Exception) as exc:
        await housing_router.messages_list_for_room(
            room_id="other-room",
            current_user=current_user,
            x_tenant_id=None,
            x_app_key=None,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_meeting_notice_posts_to_selected_restricted_room(monkeypatch):
    meetings = _Collection(
        "housing_meetings",
        rows=[
            {
                "id": "meeting-1",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "meeting_title": "MC Meeting",
                "meeting_type": "MC",
                "meeting_date": "2026-04-30",
                "meeting_time": "5:00 PM",
                "venue": "Hall",
                "notice_room_id": "mc-room",
                "agenda_items": [],
            }
        ],
    )
    rooms = _Collection(
        "housing_message_rooms",
        rows=[
            {
                "id": "mc-room",
                "tenant_id": "society-1",
                "app_key": "gruhamitra",
                "name": "MC Members",
                "type": "meeting_notices",
                "audience_type": "flats",
                "allowed_flat_numbers": ["A-101"],
            }
        ],
    )
    messages = _Collection("housing_messages")
    resolutions = _Collection("housing_meeting_resolutions")
    members = _Collection("housing_members", rows=[{"tenant_id": "society-1", "app_key": "gruhamitra", "status": "active"}])
    collections = {
        "housing_meetings": meetings,
        "housing_meeting_resolutions": resolutions,
        "housing_message_rooms": rooms,
        "housing_messages": messages,
        "housing_members": members,
    }
    monkeypatch.setattr(housing_router, "get_collection", lambda name: collections[name])

    result = await housing_router.meetings_send_notice(
        meeting_id="meeting-1",
        payload={},
        current_user={"tenant_id": "society-1", "app_key": "gruhamitra", "role": "secretary", "sub": "admin-1"},
        x_tenant_id=None,
        x_app_key=None,
    )

    assert result["message_room"]["id"] == "mc-room"
    assert messages.inserted[0]["room_id"] == "mc-room"
    assert meetings.update_queries[0] == {"tenant_id": "society-1", "app_key": "gruhamitra", "id": "meeting-1"}
