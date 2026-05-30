"""Phase 1 (MitraBooks ERP core): business COA template + org-type-aware seeding.

These tests lock in three Phase 1 guarantees:

1. A BUSINESS organization gets the dedicated business chart of accounts.
2. Every other organization type (HOUSING/TEMPLE/None) keeps the existing
   housing-style template, so live GruhaMitra/MandirMitra behavior is unchanged.
3. The canonical 5-digit account-code standard (C-SS-NNN) is enforced for the
   business COA, and each code's leading class digit matches its account type.
"""

from app.accounting.service import (
    DEFAULT_BUSINESS_CHART_OF_ACCOUNTS,
    DEFAULT_HOUSING_CHART_OF_ACCOUNTS,
    get_default_chart_of_accounts,
)

CLASS_DIGIT_TO_TYPE = {
    "1": "asset",
    "2": "liability",
    "3": "equity",
    "4": "income",
    "5": "expense",
}


def test_business_org_type_selects_business_chart() -> None:
    assert get_default_chart_of_accounts("BUSINESS") is DEFAULT_BUSINESS_CHART_OF_ACCOUNTS
    # Case/whitespace tolerant because organization_type may arrive unnormalized.
    assert get_default_chart_of_accounts("  business ") is DEFAULT_BUSINESS_CHART_OF_ACCOUNTS


def test_non_business_org_types_keep_housing_chart() -> None:
    # Backward compatibility guarantee for live tenants.
    assert get_default_chart_of_accounts("HOUSING") is DEFAULT_HOUSING_CHART_OF_ACCOUNTS
    assert get_default_chart_of_accounts("TEMPLE") is DEFAULT_HOUSING_CHART_OF_ACCOUNTS
    assert get_default_chart_of_accounts(None) is DEFAULT_HOUSING_CHART_OF_ACCOUNTS
    assert get_default_chart_of_accounts("") is DEFAULT_HOUSING_CHART_OF_ACCOUNTS
    assert get_default_chart_of_accounts("UNKNOWN") is DEFAULT_HOUSING_CHART_OF_ACCOUNTS


def test_business_chart_codes_are_unique_five_digit() -> None:
    codes = [account["code"] for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS]
    assert codes, "business chart must not be empty"
    assert len(codes) == len(set(codes)), "business account codes must be unique"
    for code in codes:
        assert code.isdigit() and len(code) == 5, f"code {code} is not 5-digit numeric"


def test_business_chart_class_digit_matches_account_type() -> None:
    for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS:
        class_digit = account["code"][0]
        assert class_digit in CLASS_DIGIT_TO_TYPE, f"unexpected class digit in {account['code']}"
        assert account["account_type"] == CLASS_DIGIT_TO_TYPE[class_digit], (
            f"account {account['code']} ({account['name']}) has type "
            f"{account['account_type']} but class digit implies "
            f"{CLASS_DIGIT_TO_TYPE[class_digit]}"
        )


def test_business_chart_covers_all_five_classes() -> None:
    classes_present = {account["code"][0] for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS}
    assert classes_present == set(CLASS_DIGIT_TO_TYPE), "business COA must span all 5 account classes"


def test_business_chart_has_core_sme_accounts() -> None:
    names = {account["name"] for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS}
    required = {
        "Cash in Hand",
        "Bank Account",
        "Sundry Debtors",
        "Sundry Creditors",
        "Sales",
        "Purchases",
        "Owner's Capital",
        "Opening Balance Equity",
    }
    missing = required - names
    assert not missing, f"business COA missing core accounts: {sorted(missing)}"


def test_business_chart_has_gst_input_and_output_accounts() -> None:
    names = {account["name"] for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS}
    for gst_account in ("Input CGST", "Input SGST", "Input IGST", "Output CGST", "Output SGST", "Output IGST"):
        assert gst_account in names, f"business COA missing GST account: {gst_account}"


def test_business_chart_marks_cash_receivable_payable_flags() -> None:
    by_name = {account["name"]: account for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS}

    assert by_name["Cash in Hand"]["is_cash_bank"] is True
    assert by_name["Bank Account"]["is_cash_bank"] is True
    assert by_name["Sundry Debtors"]["is_receivable"] is True
    assert by_name["Sundry Creditors"]["is_payable"] is True

    # Schema invariant: an account is never both receivable and payable.
    for account in DEFAULT_BUSINESS_CHART_OF_ACCOUNTS:
        assert not (account["is_receivable"] and account["is_payable"])
        # Cash/bank and receivable accounts must be assets; payables must be liabilities.
        if account["is_cash_bank"] or account["is_receivable"]:
            assert account["account_type"] == "asset"
        if account["is_payable"]:
            assert account["account_type"] == "liability"
