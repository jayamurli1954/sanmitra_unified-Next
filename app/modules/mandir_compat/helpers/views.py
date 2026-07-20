"""MandirMitra donation/seva list view and row-filter helpers.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.modules.mandir_compat.donation_compliance import compliance_public_fields
from app.modules.mandir_compat.helpers.mongo_utils import _sanitize_mongo_doc

def _receipt_number_for_donation(doc: dict[str, Any]) -> str:
    existing = str(doc.get("receipt_number") or "").strip()
    if existing:
        return existing

    donation_id = str(doc.get("donation_id") or doc.get("id") or "").strip()
    if donation_id:
        return f"DON-{donation_id[:8].upper()}"

    return f"DON-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
def _mandir_donation_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    row.pop("donor_pan", None)
    row.update(compliance_public_fields(doc))
    donation_id = str(row.get("donation_id") or row.get("id") or "").strip()
    if donation_id and not str(row.get("id") or "").strip():
        row["id"] = donation_id
    if donation_id and not str(row.get("donation_id") or "").strip():
        row["donation_id"] = donation_id

    receipt_number = _receipt_number_for_donation(row)
    row["receipt_number"] = receipt_number
    if donation_id:
        row["receipt_pdf_url"] = f"/api/v1/donations/{donation_id}/receipt/pdf"
    if not row.get("donation_date") and row.get("created_at"):
        row["donation_date"] = row.get("created_at")
    return row


def _mandir_row_date_text(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    for field in fields:
        value = str(row.get(field) or "").strip()
        if value:
            return value[:10]
    return ""


def _mandir_row_matches_search(row: dict[str, Any], query: str, fields: tuple[str, ...]) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True
    return any(normalized_query in str(row.get(field) or "").lower() for field in fields)


def _mandir_filter_rows(
    rows: list[dict[str, Any]],
    *,
    q: str | None,
    from_date: date | None,
    to_date: date | None,
    date_fields: tuple[str, ...],
    search_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    from_text = from_date.isoformat() if from_date else None
    to_text = to_date.isoformat() if to_date else None
    for row in rows:
        row_date = _mandir_row_date_text(row, date_fields)
        if from_text and row_date and row_date < from_text:
            continue
        if to_text and row_date and row_date > to_text:
            continue
        if q and not _mandir_row_matches_search(row, q, search_fields):
            continue
        filtered.append(row)
    return filtered
def _receipt_number_for_seva(doc: dict[str, Any]) -> str:
    existing = str(doc.get("receipt_number") or "").strip()
    if existing:
        return existing

    booking_id = str(doc.get("id") or doc.get("booking_id") or "").strip()
    if booking_id:
        return f"SEV-{booking_id[:8].upper()}"

    return f"SEV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _mandir_seva_booking_view(doc: dict[str, Any]) -> dict[str, Any]:
    row = _sanitize_mongo_doc(doc)
    booking_id = str(row.get("id") or row.get("booking_id") or "").strip()
    if booking_id and not str(row.get("id") or "").strip():
        row["id"] = booking_id
    receipt_number = _receipt_number_for_seva(row)
    row["receipt_number"] = receipt_number
    if booking_id:
        row["receipt_pdf_url"] = f"/api/v1/sevas/bookings/{booking_id}/receipt/pdf"
    return row


