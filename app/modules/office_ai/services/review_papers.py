"""Working paper Excel generators from MIS facts (ADR-015). No ledger access."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from openpyxl import Workbook

from app.modules.office_ai.models import REVIEW_PAPER_GENERATOR_VERSION

EXCEL_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _amount(fact: dict[str, Any]) -> Decimal:
    raw = fact.get("amount_decimal")
    if raw is None:
        return Decimal("0")
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _dims(fact: dict[str, Any]) -> dict[str, Any]:
    return dict(fact.get("dimensions") or {})


def _workbook(headers: list[str], rows: list[list[Any]], sheet_name: str) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = sheet_name[:31]
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    sheet.append([])
    sheet.append(["generator_version", REVIEW_PAPER_GENERATOR_VERSION])
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def build_cash_lead(facts: list[dict[str, Any]]) -> tuple[bytes, str]:
    rows = []
    for fact in facts:
        if fact.get("entity_type") != "cash_summary":
            continue
        dims = _dims(fact)
        rows.append(
            [
                str(dims.get("line") or fact.get("source_ref") or ""),
                str(fact.get("amount_decimal") or "0"),
                str(fact.get("currency") or "INR"),
                str(fact.get("fact_id") or ""),
            ]
        )
    content = _workbook(["Line", "Amount", "Currency", "fact_id"], rows, "Cash")
    return content, "cash_lead.xlsx"


def build_ar_lead(facts: list[dict[str, Any]]) -> tuple[bytes, str]:
    return _party_or_aging_sheet(facts, side="AR", sheet="AR", filename="ar_lead.xlsx")


def build_ap_lead(facts: list[dict[str, Any]]) -> tuple[bytes, str]:
    return _party_or_aging_sheet(facts, side="AP", sheet="AP", filename="ap_lead.xlsx")


def build_ar_aging(facts: list[dict[str, Any]]) -> tuple[bytes, str]:
    return _aging_sheet(facts, side="AR", filename="ar_aging.xlsx")


def build_ap_aging(facts: list[dict[str, Any]]) -> tuple[bytes, str]:
    return _aging_sheet(facts, side="AP", filename="ap_aging.xlsx")


def _aging_sheet(facts: list[dict[str, Any]], *, side: str, filename: str) -> tuple[bytes, str]:
    rows = []
    for fact in facts:
        if fact.get("entity_type") != "aging_bucket":
            continue
        if str(_dims(fact).get("side") or "").upper() != side:
            continue
        rows.append(
            [
                str(_dims(fact).get("bucket") or ""),
                str(fact.get("amount_decimal") or "0"),
                str(fact.get("currency") or "INR"),
                str(fact.get("fact_id") or ""),
            ]
        )
    content = _workbook(["Bucket", "Amount", "Currency", "fact_id"], rows, f"{side} Aging")
    return content, filename


def _party_or_aging_sheet(
    facts: list[dict[str, Any]],
    *,
    side: str,
    sheet: str,
    filename: str,
) -> tuple[bytes, str]:
    party_type = "customer" if side == "AR" else "vendor"
    rows = []
    for fact in facts:
        if fact.get("entity_type") == "party":
            ptype = str(_dims(fact).get("type") or "").lower()
            if ptype in {party_type, side.lower()}:
                rows.append(
                    [
                        str(_dims(fact).get("name") or fact.get("source_ref") or ""),
                        str(fact.get("amount_decimal") or "0"),
                        str(fact.get("currency") or "INR"),
                        str(fact.get("fact_id") or ""),
                    ]
                )
    if not rows:
        for fact in facts:
            if fact.get("entity_type") != "aging_bucket":
                continue
            if str(_dims(fact).get("side") or "").upper() != side:
                continue
            rows.append(
                [
                    str(_dims(fact).get("bucket") or ""),
                    str(fact.get("amount_decimal") or "0"),
                    str(fact.get("currency") or "INR"),
                    str(fact.get("fact_id") or ""),
                ]
            )
    content = _workbook(["Name / bucket", "Amount", "Currency", "fact_id"], rows, sheet)
    return content, filename


PAPER_BUILDERS = {
    "cash_lead": build_cash_lead,
    "ar_lead": build_ar_lead,
    "ap_lead": build_ap_lead,
    "ar_aging": build_ar_aging,
    "ap_aging": build_ap_aging,
}
