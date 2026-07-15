from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException


DEFAULT_DONATION_COMPLIANCE_CONFIG: dict[str, Any] = {
    "enable_80g": False,
    "enable_fcra": False,
    "certificate_label": "Donation certificate",
    "receipt_disclaimer": (
        "Eligibility is subject to applicable law and the institution's official filing; "
        "this receipt is not tax or legal advice."
    ),
}

_PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_REGISTRATION_TYPES = {"registration", "prior_permission"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _bool(value: Any) -> bool:
    return value is True or _text(value).lower() in {"1", "true", "yes", "on"}


def _date(value: Any, field: str, *, required: bool = False) -> date | None:
    text = _text(value)
    if not text:
        if required:
            raise HTTPException(status_code=422, detail=f"{field} is required")
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field} must use YYYY-MM-DD") from exc


def _positive_decimal(value: Any, field: str, *, required: bool = False) -> str | None:
    text = _text(value)
    if not text:
        if required:
            raise HTTPException(status_code=422, detail=f"{field} is required")
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise HTTPException(status_code=422, detail=f"{field} must be a decimal amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise HTTPException(status_code=422, detail=f"{field} must be greater than zero")
    return format(amount, "f")


def donation_compliance_config_view(doc: dict[str, Any] | None) -> dict[str, Any]:
    source = doc or {}
    return {
        **DEFAULT_DONATION_COMPLIANCE_CONFIG,
        "enable_80g": _bool(source.get("enable_80g", False)),
        "institution_pan": _text(source.get("institution_pan")) or None,
        "approval_number": _text(source.get("approval_number")) or None,
        "approval_valid_from": _text(source.get("approval_valid_from")) or None,
        "approval_valid_to": _text(source.get("approval_valid_to")) or None,
        "certificate_label": _text(source.get("certificate_label")) or DEFAULT_DONATION_COMPLIANCE_CONFIG["certificate_label"],
        "receipt_disclaimer": _text(source.get("receipt_disclaimer")) or DEFAULT_DONATION_COMPLIANCE_CONFIG["receipt_disclaimer"],
        "cash_eligibility_limit": _text(source.get("cash_eligibility_limit")) or None,
        "cash_rule_effective_from": _text(source.get("cash_rule_effective_from")) or None,
        "enable_fcra": _bool(source.get("enable_fcra", False)),
        "fcra_registration_type": _text(source.get("fcra_registration_type")) or None,
        "fcra_registration_number": _text(source.get("fcra_registration_number")) or None,
        "fcra_valid_from": _text(source.get("fcra_valid_from")) or None,
        "fcra_valid_to": _text(source.get("fcra_valid_to")) or None,
        "fcra_designated_account_id": _text(source.get("fcra_designated_account_id")) or None,
        "updated_at": source.get("updated_at"),
    }


def validate_donation_compliance_config(payload: dict[str, Any]) -> dict[str, Any]:
    config = donation_compliance_config_view(payload)
    if config["enable_80g"]:
        pan = _text(config["institution_pan"]).upper()
        if not _PAN_PATTERN.fullmatch(pan):
            raise HTTPException(status_code=422, detail="A valid institution_pan is required when 80G is enabled")
        if not _text(config["approval_number"]):
            raise HTTPException(status_code=422, detail="approval_number is required when 80G is enabled")
        start = _date(config["approval_valid_from"], "approval_valid_from", required=True)
        end = _date(config["approval_valid_to"], "approval_valid_to", required=True)
        if start and end and start > end:
            raise HTTPException(status_code=422, detail="approval_valid_from cannot be after approval_valid_to")
        config["institution_pan"] = pan
        config["cash_eligibility_limit"] = _positive_decimal(
            config["cash_eligibility_limit"], "cash_eligibility_limit", required=True
        )
        _date(config["cash_rule_effective_from"], "cash_rule_effective_from", required=True)

    if config["enable_fcra"]:
        registration_type = _text(config["fcra_registration_type"]).lower()
        if registration_type not in _REGISTRATION_TYPES:
            raise HTTPException(
                status_code=422,
                detail="fcra_registration_type must be registration or prior_permission",
            )
        for field in ("fcra_registration_number", "fcra_designated_account_id"):
            if not _text(config[field]):
                raise HTTPException(status_code=422, detail=f"{field} is required when FCRA is enabled")
        start = _date(config["fcra_valid_from"], "fcra_valid_from", required=True)
        end = _date(config["fcra_valid_to"], "fcra_valid_to", required=True)
        if start and end and start > end:
            raise HTTPException(status_code=422, detail="fcra_valid_from cannot be after fcra_valid_to")
        config["fcra_registration_type"] = registration_type
    return config


def _active_on(config: dict[str, Any], prefix: str, on_date: date) -> bool:
    start = _date(config.get(f"{prefix}_valid_from"), f"{prefix}_valid_from")
    end = _date(config.get(f"{prefix}_valid_to"), f"{prefix}_valid_to")
    return bool(start and end and start <= on_date <= end)


def classify_donation_compliance(
    payload: dict[str, Any],
    config_doc: dict[str, Any] | None,
    *,
    amount: Decimal,
    donation_type: str,
    payment_mode: str,
    donation_date: date,
    payment_account_id: str | None,
) -> dict[str, Any]:
    config = donation_compliance_config_view(config_doc)
    request_80g = _bool(payload.get("request_80g", False))
    is_foreign = _bool(payload.get("is_foreign_contribution", False))
    result: dict[str, Any] = {
        "request_80g": request_80g,
        "is_foreign_contribution": is_foreign,
        "80g_eligibility_status": "not_requested",
        "fcra_status": "not_applicable",
    }

    donor_pan = _text(payload.get("donor_pan")).upper()
    if donor_pan and not _PAN_PATTERN.fullmatch(donor_pan):
        raise HTTPException(status_code=422, detail="donor_pan is invalid")

    if request_80g:
        status = "eligible"
        if not config["enable_80g"]:
            status = "not_available"
        elif not _active_on(config, "approval", donation_date):
            status = "approval_not_valid"
        elif donation_type == "in_kind":
            status = "ineligible_in_kind"
        elif not donor_pan:
            status = "missing_donor_pan"
        else:
            rule_date = _date(config.get("cash_rule_effective_from"), "cash_rule_effective_from")
            limit = Decimal(_text(config.get("cash_eligibility_limit")) or "0")
            if payment_mode.lower() == "cash" and rule_date and donation_date >= rule_date and amount > limit:
                status = "ineligible_cash_limit"
        result.update({
            "80g_eligibility_status": status,
            "donor_pan": donor_pan or None,
            "80g_approval_number": config.get("approval_number") if config["enable_80g"] else None,
            "80g_approval_valid_from": config.get("approval_valid_from") if config["enable_80g"] else None,
            "80g_approval_valid_to": config.get("approval_valid_to") if config["enable_80g"] else None,
            "80g_certificate_label": config.get("certificate_label"),
            "80g_receipt_disclaimer": config.get("receipt_disclaimer"),
        })

    if is_foreign:
        if not config["enable_fcra"]:
            raise HTTPException(status_code=409, detail="Foreign contribution cannot be accepted because FCRA is disabled")
        if not _active_on(config, "fcra", donation_date):
            raise HTTPException(status_code=409, detail="Foreign contribution cannot be accepted because FCRA approval is not valid")
        country = _text(payload.get("donor_country"))
        if not country:
            raise HTTPException(status_code=422, detail="donor_country is required for foreign contribution")
        if not _bool(payload.get("foreign_source_declaration", False)):
            raise HTTPException(status_code=422, detail="foreign_source_declaration is required for foreign contribution")
        designated = _text(config.get("fcra_designated_account_id"))
        if not payment_account_id or _text(payment_account_id) != designated:
            raise HTTPException(status_code=409, detail="Foreign contribution must use the configured designated FCRA account")
        result.update({
            "fcra_status": "accepted",
            "donor_country": country,
            "foreign_source_declaration": True,
            "fcra_registration_type": config.get("fcra_registration_type"),
            "fcra_registration_number": config.get("fcra_registration_number"),
            "fcra_valid_from": config.get("fcra_valid_from"),
            "fcra_valid_to": config.get("fcra_valid_to"),
            "fcra_designated_account_id": designated,
        })
    return result


def mask_pan(value: Any) -> str | None:
    pan = _text(value)
    return f"*****{pan[-4:]}" if pan else None


def compliance_public_fields(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_80g": bool(doc.get("request_80g")),
        "80g_eligibility_status": _text(doc.get("80g_eligibility_status")) or "not_requested",
        "donor_pan_masked": mask_pan(doc.get("donor_pan")),
        "is_foreign_contribution": bool(doc.get("is_foreign_contribution")),
        "fcra_status": _text(doc.get("fcra_status")) or "not_applicable",
        "donor_country": _text(doc.get("donor_country")) or None,
    }


def donation_compliance_receipt_note(doc: dict[str, Any]) -> str:
    notes: list[str] = []
    status = _text(doc.get("80g_eligibility_status"))
    if status == "eligible":
        label = _text(doc.get("80g_certificate_label")) or "Donation certificate"
        approval = _text(doc.get("80g_approval_number"))
        notes.append(f"80G eligible; {label} reference: {approval}. Donor PAN: {mask_pan(doc.get('donor_pan'))}.")
        disclaimer = _text(doc.get("80g_receipt_disclaimer"))
        if disclaimer:
            notes.append(disclaimer)
    elif bool(doc.get("request_80g")):
        notes.append(f"This receipt is not marked 80G eligible (status: {status or 'not_available'}).")
    if bool(doc.get("is_foreign_contribution")):
        notes.append(
            "Foreign contribution recorded under "
            f"{_text(doc.get('fcra_registration_type')).replace('_', ' ')} "
            f"reference {_text(doc.get('fcra_registration_number'))}."
        )
    return " ".join(notes)
