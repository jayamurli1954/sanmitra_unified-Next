from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from types import SimpleNamespace

import app.modules.mandir_compat.router as mandir_router
from app.modules.mandir_compat.donation_compliance import (
    classify_donation_compliance,
    compliance_public_fields,
    donation_compliance_config_view,
    donation_compliance_receipt_note,
    validate_donation_compliance_config,
)


def enabled_config(**overrides):
    config = {
        "enable_80g": True,
        "institution_pan": "ABCDE1234F",
        "approval_number": "APPROVAL-2026-1",
        "approval_valid_from": "2026-01-01",
        "approval_valid_to": "2026-12-31",
        "certificate_label": "Tenant-configured donation certificate",
        "receipt_disclaimer": "Subject to official filing and applicable law.",
        "cash_eligibility_limit": "2000.00",
        "cash_rule_effective_from": "2026-04-01",
        "enable_fcra": True,
        "fcra_registration_type": "registration",
        "fcra_registration_number": "FCRA-DEMO-1",
        "fcra_valid_from": "2026-01-01",
        "fcra_valid_to": "2026-12-31",
        "fcra_designated_account_id": "bank-fcra-1",
    }
    config.update(overrides)
    return validate_donation_compliance_config(config)


def classify(payload, config, *, amount="1000.00", mode="bank", donation_type="cash", account="bank-1"):
    return classify_donation_compliance(
        payload,
        config,
        amount=Decimal(amount),
        donation_type=donation_type,
        payment_mode=mode,
        donation_date=date(2026, 7, 13),
        payment_account_id=account,
    )


def test_compliance_defaults_are_off_and_do_not_claim_eligibility():
    config = donation_compliance_config_view(None)
    assert config["enable_80g"] is False
    assert config["enable_fcra"] is False

    result = classify({"request_80g": True, "donor_pan": "ABCDE1234F"}, None)
    assert result["80g_eligibility_status"] == "not_available"
    assert result["fcra_status"] == "not_applicable"


def test_enabled_config_requires_tenant_evidence_and_valid_dates():
    with pytest.raises(HTTPException, match="institution_pan"):
        enabled_config(institution_pan="invalid")
    with pytest.raises(HTTPException, match="approval_valid_from"):
        enabled_config(approval_valid_from="2027-01-01")
    with pytest.raises(HTTPException, match="fcra_designated_account_id"):
        enabled_config(fcra_designated_account_id="")


def test_80g_eligibility_uses_configured_effective_cash_rule_and_masks_pan():
    config = enabled_config()
    eligible = classify(
        {"request_80g": True, "donor_pan": "ABCDE1234F"}, config, mode="upi"
    )
    assert eligible["80g_eligibility_status"] == "eligible"
    public = compliance_public_fields(eligible)
    assert public["donor_pan_masked"] == "*****234F"
    assert "ABCDE1234F" not in str(public)
    assert "Tenant-configured donation certificate" in donation_compliance_receipt_note(eligible)

    cash = classify(
        {"request_80g": True, "donor_pan": "ABCDE1234F"},
        config,
        amount="2000.01",
        mode="cash",
    )
    assert cash["80g_eligibility_status"] == "ineligible_cash_limit"
    assert "not marked 80G eligible" in donation_compliance_receipt_note(cash)

    in_kind = classify(
        {"request_80g": True, "donor_pan": "ABCDE1234F"},
        config,
        donation_type="in_kind",
    )
    assert in_kind["80g_eligibility_status"] == "ineligible_in_kind"


def test_foreign_contribution_is_fail_closed_and_uses_designated_account():
    payload = {
        "is_foreign_contribution": True,
        "donor_country": "United States",
        "foreign_source_declaration": True,
    }
    with pytest.raises(HTTPException, match="FCRA is disabled"):
        classify(payload, None)

    config = enabled_config()
    with pytest.raises(HTTPException, match="designated FCRA account"):
        classify(payload, config, account="ordinary-bank")

    accepted = classify(payload, config, account="bank-fcra-1")
    assert accepted["fcra_status"] == "accepted"
    assert accepted["fcra_registration_number"] == "FCRA-DEMO-1"
    note = donation_compliance_receipt_note(accepted)
    assert "Foreign contribution recorded" in note
    assert "bank-fcra-1" not in note


def test_expired_approvals_never_mark_receipt_eligible_or_accept_foreign_funds():
    config = enabled_config(approval_valid_to="2026-06-30", fcra_valid_to="2026-06-30")
    result = classify({"request_80g": True, "donor_pan": "ABCDE1234F"}, config)
    assert result["80g_eligibility_status"] == "approval_not_valid"

    with pytest.raises(HTTPException, match="approval is not valid"):
        classify(
            {
                "is_foreign_contribution": True,
                "donor_country": "Singapore",
                "foreign_source_declaration": True,
            },
            config,
            account="bank-fcra-1",
        )


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])

    async def find_one(self, query):
        return next((dict(row) for row in self.docs if all(row.get(k) == v for k, v in query.items())), None)

    async def update_one(self, query, update, **kwargs):
        row = next((row for row in self.docs if all(row.get(k) == v for k, v in query.items())), None)
        if row is None and kwargs.get("upsert"):
            row = {**query, **update.get("$setOnInsert", {})}
            self.docs.append(row)
        row.update(update.get("$set", {}))
        return SimpleNamespace(modified_count=1)


@pytest.mark.asyncio
async def test_config_routes_are_exact_tenant_app_scoped_and_audit_excludes_sensitive_values(monkeypatch):
    collection = FakeCollection([
        {"tenant_id": "other", "app_key": "mandirmitra", **enabled_config(approval_number="OTHER")},
    ])
    monkeypatch.setattr(mandir_router, "get_collection", lambda _name: collection)
    audits = []

    async def audit(**kwargs):
        audits.append(kwargs)

    monkeypatch.setattr(mandir_router, "log_audit_event", audit)
    user = {"sub": "admin-1", "tenant_id": "tenant-1", "app_key": "mandirmitra", "role": "tenant_admin"}
    saved = await mandir_router.update_mandir_donation_compliance_config(
        enabled_config(), user, None, "mandirmitra"
    )
    assert saved["approval_number"] == "APPROVAL-2026-1"
    assert {row["tenant_id"] for row in collection.docs} == {"tenant-1", "other"}
    assert collection.docs[0]["approval_number"] == "OTHER"
    assert "institution_pan" not in audits[0]["new_value"]
    assert "fcra_designated_account_id" not in audits[0]["new_value"]

    loaded = await mandir_router.get_mandir_donation_compliance_config(user, None, "mandirmitra")
    assert loaded["approval_number"] == "APPROVAL-2026-1"


@pytest.mark.asyncio
async def test_readiness_report_is_not_a_filing_and_never_exposes_full_pan(monkeypatch):
    async def posted(*_args, **_kwargs):
        return [{
            "donation_id": "don-1", "receipt_number": "DON-1", "date": "2026-07-13",
            "amount": 500.0, "payment_mode": "UPI", "devotee_name": "Donor",
            "request_80g": True, "80g_eligibility_status": "eligible", "donor_pan": "ABCDE1234F",
            "is_foreign_contribution": False, "fcra_status": "not_applicable",
        }]

    monkeypatch.setattr(mandir_router, "posted_donations", posted)
    report = await mandir_router._mandir_compliance_report(
        kind="80g", tenant_id="tenant-1", app_key="mandirmitra",
        from_date=date(2026, 7, 13), to_date=date(2026, 7, 13), session=SimpleNamespace(),
    )
    assert report["filing_artifact"] is False
    assert report["status_counts"] == {"eligible": 1}
    assert report["items"][0]["donor_pan_masked"] == "*****234F"
    assert "ABCDE1234F" not in str(report)
