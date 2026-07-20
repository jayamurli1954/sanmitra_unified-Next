"""MandirMitra donation read-only routes (list, categories, receipt PDF).

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any

from fastapi import Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.auth.dependencies import get_current_user
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import router

@router.get("/donations/payment-accounts")
async def donations_payment_accounts(
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())
    return await mandir_router._payment_accounts(tenant_id, app_key)


@router.get("/donations/categories/")
@router.get("/donations/categories")
async def donations_categories(_current_user: dict = Depends(get_current_user)):
    return [
        {"id": "general", "name": "General Donation"},
        {"id": "annadanam", "name": "Annadanam"},
        {"id": "construction", "name": "Construction Fund"},
        {"id": "corpus", "name": "Corpus Fund"},
    ]
@router.get("/donations")
async def list_donations(
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    payment_mode: str | None = Query(default=None),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be greater than to_date")
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    try:
        col = mandir_router.get_collection("mandir_donations")
        fetch_limit = 2000 if any([q, from_date, to_date, payment_mode]) else min(limit + offset, 2000)
        rows = await col.find({"tenant_id": tenant_id, "app_key": app_key}).sort("created_at", -1).limit(fetch_limit).to_list(length=fetch_limit)
    except Exception as exc:
        mandir_router.logger.error("Failed to list donations for tenant=%s: %s", tenant_id, exc, exc_info=True)
        rows = []

    viewed = [mandir_router._mandir_donation_view(row) for row in rows]
    if payment_mode:
        normalized_mode = str(payment_mode).strip().lower()
        viewed = [row for row in viewed if str(row.get("payment_mode") or "").strip().lower() == normalized_mode]
    filtered = mandir_router._mandir_filter_rows(
        viewed,
        q=q,
        from_date=from_date,
        to_date=to_date,
        date_fields=("donation_date", "created_at"),
        search_fields=("receipt_number", "devotee_name", "donor_name", "name", "category", "upi_reference_number"),
    )
    return filtered[offset:offset + limit]
@router.get("/donations/{donation_id}/receipt/pdf")
async def get_donation_receipt_pdf(
    donation_id: str,
    lang: str | None = Query(default=None, description="Override receipt language (kannada/hindi/tamil/telugu/malayalam)"),
    current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or current_user.get("app_key") or "mandirmitra").strip())

    col = mandir_router.get_collection("mandir_donations")
    donation = await col.find_one({"tenant_id": tenant_id, "app_key": app_key, "donation_id": donation_id})
    if donation is None:
        donation = await col.find_one({"tenant_id": tenant_id, "app_key": app_key, "id": donation_id})
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    donation_id_text = str(donation.get("donation_id") or donation.get("id") or donation_id).strip()
    donation["donation_id"] = donation_id_text
    donation["id"] = donation_id_text
    receipt_number = mandir_router._receipt_number_for_donation(donation)
    donation["receipt_number"] = receipt_number
    donation["receipt_pdf_url"] = f"/api/v1/donations/{donation_id_text}/receipt/pdf"

    await col.update_one(
        {"tenant_id": tenant_id, "app_key": app_key, "donation_id": donation_id_text},
        {
            "$set": {
                "id": donation_id_text,
                "receipt_number": receipt_number,
                "receipt_pdf_url": donation["receipt_pdf_url"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=False,
    )

    temple_profile = await mandir_router._resolve_temple_receipt_profile(tenant_id=tenant_id, app_key=app_key, lang=lang)

    try:
        pdf_bytes = mandir_router._generate_donation_receipt_pdf_bytes(
            donation,
            temple_name=temple_profile.get("temple_name", "Temple"),
            temple_profile=temple_profile,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    safe_receipt = "".join(ch for ch in str(receipt_number) if ch.isalnum() or ch in ("-", "_")) or donation_id_text[:8]
    filename = f"donation_receipt_{safe_receipt}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

