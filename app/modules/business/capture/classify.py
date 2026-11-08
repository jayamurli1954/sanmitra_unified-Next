"""Document-type classification and accounting-treatment derivation.

Takes the extracted fields and decides WHAT the document is and HOW it should be
booked — including the India-specific cases:
  * unregistered / no-GSTIN local purchase  -> no ITC, flag possible RCM
  * registered purchase with GST            -> input GST / ITC
  * sales invoice                           -> output GST
  * expense voucher / income receipt        -> cash/bank legs, usually no ITC

This is a proposal for the human reviewer, never an auto-post. Deterministic and
pure (no model, no I/O) so it is fully testable.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from app.modules.business.capture.validators import gstin_check_digit_ok

DOC_TYPES = {
    "purchase_bill",
    "sales_invoice",
    "expense_voucher",
    "income_receipt",
    "credit_note",
    "debit_note",
    "bank_statement",
    "unknown",
}


def _dec(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _total_tax(fields: dict[str, Any]) -> Decimal:
    explicit = _dec(fields.get("tax_amount"))
    if explicit is not None:
        return explicit
    total = Decimal("0")
    for key in ("cgst_amount", "sgst_amount", "igst_amount"):
        part = _dec(fields.get(key))
        if part is not None:
            total += part
    return total


def _normalize_type(hint: str | None) -> str:
    dt = str(hint or "").strip().lower()
    if dt in DOC_TYPES:
        return dt
    aliases = {
        "bill": "purchase_bill",
        "purchase": "purchase_bill",
        "invoice": "sales_invoice",
        "sales": "sales_invoice",
        "receipt": "income_receipt",
        "expense": "expense_voucher",
        "voucher": "expense_voucher",
    }
    return aliases.get(dt, "unknown")


def classify(*, document_type_hint: str | None, fields: dict[str, Any]) -> dict[str, Any]:
    doc_type = _normalize_type(document_type_hint)
    gstin = fields.get("vendor_gstin")
    registered = bool(gstin) and gstin_check_digit_ok(gstin)
    registration_status = "registered" if registered else "unregistered"
    tax = _total_tax(fields)
    has_gst = tax > 0

    itc_eligible: bool | None = None
    possible_rcm = False
    treatment = "review_required"

    if doc_type in ("purchase_bill", "expense_voucher"):
        if registered and has_gst:
            itc_eligible = True
            treatment = "purchase_input_gst"
        else:
            # Unregistered / no-GSTIN local purchase: no input tax to claim.
            itc_eligible = False
            # RCM can apply to purchases from unregistered dealers on notified
            # supplies — surface it for the human, never decide it silently.
            possible_rcm = doc_type == "purchase_bill" and not registered
            treatment = "purchase_no_itc_rcm_check" if possible_rcm else "purchase_no_itc"
    elif doc_type == "sales_invoice":
        treatment = "sales_output_gst" if has_gst else "sales_no_gst"
    elif doc_type == "income_receipt":
        treatment = "other_income_receipt"
    elif doc_type in ("credit_note", "debit_note"):
        treatment = f"{doc_type}_adjustment"
    elif doc_type == "bank_statement":
        treatment = "bank_reconciliation"

    return {
        "doc_type": doc_type,
        "registration_status": registration_status,
        "itc_eligible": itc_eligible,
        "possible_rcm": possible_rcm,
        "treatment": treatment,
    }
