"""MandirMitra devotee lookup/upsert and UPI payment view helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.helpers.coercions import (
    _normalize_phone,
    _safe_float,
)
from app.modules.mandir_compat.helpers.mongo_utils import _sanitize_mongo_doc

def _upi_receipt_number(doc: dict[str, Any]) -> str:
    existing = str(doc.get("receipt_number") or "").strip()
    if existing:
        return existing

    row_id = str(doc.get("id") or "").strip()
    if row_id:
        return f"UPI-{row_id[:8].upper()}"

    return f"UPI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _mandir_upi_payment_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    row_id = str(row.get("id") or "").strip()
    if row_id:
        row["id"] = row_id

    row["amount"] = _safe_float(row.get("amount"), 0.0)
    row["payment_purpose"] = str(row.get("payment_purpose") or "DONATION").strip().upper()
    row["receipt_number"] = _upi_receipt_number(row)
    if not row.get("payment_datetime"):
        row["payment_datetime"] = row.get("created_at")

    row["sender_phone"] = _normalize_phone(row.get("sender_phone") or row.get("devotee_phone"))
    row["devotee_phone"] = _normalize_phone(row.get("devotee_phone") or row.get("sender_phone"))
    return row


async def _find_devotee_by_phone(
    tenant_id: str,
    app_key: str,
    phone: str,
    temple_id: int | None = None,
) -> dict[str, Any] | None:
    normalized = _normalize_phone(phone)
    if not normalized:
        return None

    scope_query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key}
    if temple_id is not None and temple_id > 0:
        scope_query["temple_id"] = temple_id

    legacy_scope_query: dict[str, Any] | None = None
    if temple_id is not None and temple_id > 0:
        # Older MandirMitra donation/seva-derived devotee data was tenant-scoped
        # but did not persist temple_id. Keep this fallback inside the resolved
        # tenant/app and only match records with no explicit temple assignment.
        legacy_scope_query = {"tenant_id": tenant_id, "app_key": app_key, "temple_id": None}

    devotee_col = mandir_router.get_collection("mandir_devotees")
    docs = await devotee_col.find({**scope_query, "phone": normalized}).limit(1).to_list(length=1)
    if docs:
        return _sanitize_mongo_doc(docs[0])
    if legacy_scope_query is not None:
        docs = await devotee_col.find({**legacy_scope_query, "phone": normalized}).limit(1).to_list(length=1)
        if docs:
            devotee = _sanitize_mongo_doc(docs[0])
            devotee["temple_id"] = temple_id
            return devotee

    donation_col = mandir_router.get_collection("mandir_donations")
    donation_docs = await (
        donation_col.find({**scope_query, "devotee_phone": normalized})
        .sort("created_at", -1)
        .limit(1)
        .to_list(length=1)
    )
    if donation_docs:
        donation = _sanitize_mongo_doc(donation_docs[0])
        snapshot = donation.get("devotee") if isinstance(donation.get("devotee"), dict) else {}
        return {
            "id": str(snapshot.get("id") or donation.get("devotee_id") or f"donation:{donation.get('donation_id') or donation.get('id')}"),
            "tenant_id": tenant_id,
            "app_key": app_key,
            "temple_id": temple_id,
            "name_prefix": donation.get("devotee_prefix") or snapshot.get("name_prefix"),
            "name": donation.get("devotee_name") or snapshot.get("name") or "Devotee",
            "first_name": donation.get("devotee_name") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
            "last_name": snapshot.get("last_name") or "",
            "phone": normalized,
            "email": donation.get("devotee_email") or snapshot.get("email"),
            "address": donation.get("devotee_address") or snapshot.get("address"),
            "city": donation.get("devotee_city") or snapshot.get("city"),
            "state": donation.get("devotee_state") or snapshot.get("state"),
            "pincode": donation.get("devotee_pincode") or snapshot.get("pincode"),
            "source": "donation",
        }
    if legacy_scope_query is not None:
        donation_docs = await (
            donation_col.find({**legacy_scope_query, "devotee_phone": normalized})
            .sort("created_at", -1)
            .limit(1)
            .to_list(length=1)
        )
        if donation_docs:
            donation = _sanitize_mongo_doc(donation_docs[0])
            snapshot = donation.get("devotee") if isinstance(donation.get("devotee"), dict) else {}
            return {
                "id": str(snapshot.get("id") or donation.get("devotee_id") or f"donation:{donation.get('donation_id') or donation.get('id')}"),
                "tenant_id": tenant_id,
                "app_key": app_key,
                "temple_id": temple_id,
                "name_prefix": donation.get("devotee_prefix") or snapshot.get("name_prefix"),
                "name": donation.get("devotee_name") or snapshot.get("name") or "Devotee",
                "first_name": donation.get("devotee_name") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
                "last_name": snapshot.get("last_name") or "",
                "phone": normalized,
                "email": donation.get("devotee_email") or snapshot.get("email"),
                "address": donation.get("devotee_address") or snapshot.get("address"),
                "city": donation.get("devotee_city") or snapshot.get("city"),
                "state": donation.get("devotee_state") or snapshot.get("state"),
                "pincode": donation.get("devotee_pincode") or snapshot.get("pincode"),
                "source": "donation",
            }

    seva_col = mandir_router.get_collection("mandir_seva_bookings")
    seva_docs = await (
        seva_col.find({**scope_query, "devotee_phone": normalized})
        .sort("created_at", -1)
        .limit(1)
        .to_list(length=1)
    )
    if seva_docs:
        seva = _sanitize_mongo_doc(seva_docs[0])
        snapshot = seva.get("devotee") if isinstance(seva.get("devotee"), dict) else {}
        return {
            "id": str(snapshot.get("id") or seva.get("devotee_id") or f"seva:{seva.get('booking_id') or seva.get('id')}"),
            "tenant_id": tenant_id,
            "app_key": app_key,
            "temple_id": temple_id,
            "name_prefix": seva.get("devotee_prefix") or snapshot.get("name_prefix"),
            "name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("name") or "Devotee",
            "first_name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
            "last_name": snapshot.get("last_name") or "",
            "phone": normalized,
            "email": seva.get("devotee_email") or snapshot.get("email"),
            "address": seva.get("devotee_address") or seva.get("address") or snapshot.get("address"),
            "city": seva.get("devotee_city") or seva.get("city") or snapshot.get("city"),
            "state": seva.get("devotee_state") or seva.get("state") or snapshot.get("state"),
            "pincode": seva.get("devotee_pincode") or seva.get("pincode") or snapshot.get("pincode"),
            "source": "seva",
        }
    if legacy_scope_query is not None:
        seva_docs = await (
            seva_col.find({**legacy_scope_query, "devotee_phone": normalized})
            .sort("created_at", -1)
            .limit(1)
            .to_list(length=1)
        )
        if seva_docs:
            seva = _sanitize_mongo_doc(seva_docs[0])
            snapshot = seva.get("devotee") if isinstance(seva.get("devotee"), dict) else {}
            return {
                "id": str(snapshot.get("id") or seva.get("devotee_id") or f"seva:{seva.get('booking_id') or seva.get('id')}"),
                "tenant_id": tenant_id,
                "app_key": app_key,
                "temple_id": temple_id,
                "name_prefix": seva.get("devotee_prefix") or snapshot.get("name_prefix"),
                "name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("name") or "Devotee",
                "first_name": seva.get("devotee_name") or seva.get("devotee_names") or snapshot.get("first_name") or snapshot.get("name") or "Devotee",
                "last_name": snapshot.get("last_name") or "",
                "phone": normalized,
                "email": seva.get("devotee_email") or snapshot.get("email"),
                "address": seva.get("devotee_address") or seva.get("address") or snapshot.get("address"),
                "city": seva.get("devotee_city") or seva.get("city") or snapshot.get("city"),
                "state": seva.get("devotee_state") or seva.get("state") or snapshot.get("state"),
                "pincode": seva.get("devotee_pincode") or seva.get("pincode") or snapshot.get("pincode"),
                "source": "seva",
            }

    return None


async def _upsert_devotee_from_contribution(
    tenant_id: str,
    app_key: str,
    *,
    temple_id: int | None = None,
    phone: str | None,
    name_prefix: str | None = None,
    name: str | None = None,
    email: str | None = None,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    pincode: str | None = None,
) -> None:
    normalized = _normalize_phone(phone)
    if not normalized:
        return

    now = datetime.now(timezone.utc).isoformat()
    devotee_patch: dict[str, Any] = {"updated_at": now}
    if temple_id is not None and temple_id > 0:
        devotee_patch["temple_id"] = temple_id
    for key, value in {
        "name_prefix": name_prefix,
        "name": name,
        "first_name": name,
        "email": email,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
    }.items():
        if value not in (None, ""):
            devotee_patch[key] = value

    col = mandir_router.get_collection("mandir_devotees")
    query: dict[str, Any] = {"tenant_id": tenant_id, "app_key": app_key, "phone": normalized}
    if temple_id is not None and temple_id > 0:
        query["temple_id"] = temple_id

    insert_doc: dict[str, Any] = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "app_key": app_key,
        "phone": normalized,
        "created_at": now,
    }
    if temple_id is not None and temple_id > 0:
        insert_doc["temple_id"] = temple_id

    await col.update_one(
        query,
        {
            "$setOnInsert": insert_doc,
            "$set": devotee_patch,
        },
        upsert=True,
    )


def _build_upi_intent_uri(
    *,
    upi_id: str,
    payee_name: str,
    amount: float | None,
    note: str | None,
    reference: str | None,
    currency: str = "INR",
) -> str:
    params: list[tuple[str, str]] = [("pa", upi_id), ("pn", payee_name), ("cu", currency)]
    if amount is not None and amount > 0:
        params.append(("am", f"{amount:.2f}"))
    if note:
        params.append(("tn", note))
    if reference:
        params.append(("tr", reference))
    return f"upi://pay?{urlencode(params)}"

