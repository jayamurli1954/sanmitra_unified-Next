from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.db.mongo import get_collection


def pdf_text(value: Any) -> str:
    return str(value or "").encode("latin-1", errors="replace").decode("latin-1")


async def get_housing_society_branding(*, tenant_id: str, app_key: str) -> dict[str, Any]:
    settings = await get_collection("housing_society_settings").find_one(
        {"tenant_id": tenant_id, "app_key": app_key}
    ) or {}
    logo_url = str(settings.get("logo_url") or "").strip()
    logo_name = logo_url.rstrip("/").split("/")[-1] if logo_url else ""
    if not logo_name:
        logo_doc = await get_collection("housing_documents").find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "document_type": "society_logo"},
            sort=[("updated_at", -1)],
        )
        if logo_doc:
            logo_name = str(logo_doc.get("stored_name") or "").strip()

    logo_bytes = b""
    if logo_name:
        logo_doc = await get_collection("housing_documents").find_one(
            {"tenant_id": tenant_id, "app_key": app_key, "stored_name": logo_name},
            {"content": 1},
        )
        logo_bytes = bytes(logo_doc.get("content") or b"") if logo_doc else b""

    return {
        "society_name": str(settings.get("society_name") or "GruhaMitra Society").strip(),
        "society_address": str(settings.get("society_address") or "").strip(),
        "city": str(settings.get("city") or "").strip(),
        "state": str(settings.get("state") or "").strip(),
        "pin_code": str(settings.get("pin_code") or "").strip(),
        "contact_email": str(settings.get("contact_email") or "").strip(),
        "contact_phone": str(settings.get("contact_phone") or "").strip(),
        "logo_bytes": logo_bytes,
    }


def society_contact_line(branding: dict[str, Any]) -> str:
    parts = [
        str(branding.get("contact_phone") or "").strip(),
        str(branding.get("contact_email") or "").strip(),
    ]
    return " | ".join(part for part in parts if part)


def draw_society_pdf_header(
    pdf: canvas.Canvas,
    *,
    title: str,
    branding: dict[str, Any] | None,
    margin_x: int = 42,
) -> float:
    branding = branding or {}
    page_w, page_h = A4
    y_top = page_h - 38
    logo_bytes = branding.get("logo_bytes") or b""
    text_x = margin_x
    if logo_bytes:
        try:
            img = ImageReader(BytesIO(logo_bytes))
            pdf.drawImage(img, margin_x, y_top - 48, width=42, height=42, preserveAspectRatio=True, mask="auto")
            text_x = margin_x + 52
        except Exception:
            text_x = margin_x

    society_name = str(branding.get("society_name") or "GruhaMitra Society").strip()
    locality = ", ".join(
        part
        for part in [
            str(branding.get("city") or "").strip(),
            str(branding.get("state") or "").strip(),
            str(branding.get("pin_code") or "").strip(),
        ]
        if part
    )
    address_lines = [
        str(branding.get("society_address") or "").strip(),
        locality,
    ]
    contact_line = society_contact_line(branding)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(text_x, y_top, pdf_text(society_name)[:75])
    pdf.setFont("Helvetica", 9)
    y = y_top - 14
    for line in address_lines:
        if line:
            pdf.drawString(text_x, y, pdf_text(line)[:110])
            y -= 11
    if contact_line:
        pdf.drawString(text_x, y, pdf_text(contact_line)[:110])
        y -= 11

    pdf.setLineWidth(0.8)
    pdf.line(margin_x, y - 2, page_w - margin_x, y - 2)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin_x, y - 20, pdf_text(title)[:95])
    return y - 42

