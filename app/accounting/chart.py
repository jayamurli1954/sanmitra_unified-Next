"""Chart of accounts templates and account CRUD.

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.common import AccountingNotFoundError, AccountingValidationError, _accounting_scope
from app.accounting.models import Account

def _default_account(
    code: str,
    name: str,
    account_type: str,
    classification: str,
    *,
    is_cash_bank: bool = False,
    is_receivable: bool = False,
    is_payable: bool = False,
) -> dict:
    return {
        "code": code,
        "name": name,
        "account_type": account_type,
        "classification": classification,
        "is_cash_bank": is_cash_bank,
        "is_receivable": is_receivable,
        "is_payable": is_payable,
    }


DEFAULT_HOUSING_CHART_OF_ACCOUNTS = [
    _default_account("11001", "Cash in Hand", "asset", "real", is_cash_bank=True),
    _default_account("11010", "Bank Account", "asset", "real", is_cash_bank=True),
    _default_account("11011", "Savings Bank Account", "asset", "real", is_cash_bank=True),
    _default_account("15010", "Fixed Deposits", "asset", "real"),
    _default_account("12003", "Accrued Interest Receivable", "asset", "personal", is_receivable=True),
    _default_account("12001", "Member Dues Receivable", "asset", "personal", is_receivable=True),
    _default_account("12002", "Late Fee Receivable", "asset", "personal", is_receivable=True),
    _default_account("12004", "Other Receivables", "asset", "personal", is_receivable=True),
    _default_account("13002", "Advance to Vendors", "asset", "personal"),
    _default_account("15001", "Prepaid Expenses", "asset", "real"),
    _default_account("15002", "Security Deposits Paid", "asset", "real"),
    _default_account("16001", "Furniture and Fixtures", "asset", "real"),
    _default_account("16002", "Office Equipment", "asset", "real"),
    _default_account("16003", "Common Area Equipment", "asset", "real"),
    _default_account("24001", "Advance from Members", "liability", "personal"),
    _default_account("24002", "Security Deposits Received", "liability", "personal"),
    _default_account("21001", "Accounts Payable", "liability", "personal", is_payable=True),
    _default_account("21002", "Expense Payable", "liability", "personal", is_payable=True),
    _default_account("23002", "Statutory Dues Payable", "liability", "personal", is_payable=True),
    _default_account("23001", "TDS Payable", "liability", "personal", is_payable=True),
    _default_account("31001", "Maintenance Fund", "equity", "nominal"),
    _default_account("31002", "Corpus Fund", "equity", "nominal"),
    _default_account("31003", "Sinking Fund", "equity", "nominal"),
    _default_account("31004", "Reserve Fund", "equity", "nominal"),
    _default_account("31005", "Repair and Replacement Fund", "equity", "nominal"),
    _default_account("31006", "Building Fund", "equity", "nominal"),
    _default_account("31099", "Opening Balance Equity", "equity", "nominal"),
    _default_account("41001", "Member Dues Income", "income", "nominal"),
    _default_account("41002", "Late Fee Income", "income", "nominal"),
    _default_account("41003", "Parking Charges Income", "income", "nominal"),
    _default_account("41004", "Facility Booking Income", "income", "nominal"),
    _default_account("42001", "Interest Income", "income", "nominal"),
    _default_account("41005", "Water Charges Income", "income", "nominal"),
    _default_account("41006", "Transfer Fee Income", "income", "nominal"),
    _default_account("42002", "Miscellaneous Income", "income", "nominal"),
    _default_account("53005", "Repairs and Maintenance Expense", "expense", "nominal"),
    _default_account("53002", "Utilities Expense", "expense", "nominal"),
    _default_account("52001", "Security Expense", "expense", "nominal"),
    _default_account("53003", "Housekeeping Expense", "expense", "nominal"),
    _default_account("53004", "Lift Maintenance Expense", "expense", "nominal"),
    _default_account("53006", "Common Area Electricity Expense", "expense", "nominal"),
    _default_account("53007", "Water Supply Expense", "expense", "nominal"),
    _default_account("53008", "Insurance Expense", "expense", "nominal"),
    _default_account("54002", "Administrative Expense", "expense", "nominal"),
    _default_account("54001", "Bank Charges", "expense", "nominal"),
    _default_account("54003", "Legal and Professional Fees", "expense", "nominal"),
    _default_account("53009", "Garden Maintenance Expense", "expense", "nominal"),
    _default_account("53010", "Pest Control Expense", "expense", "nominal"),
]


# Shared base Chart of Accounts for MitraBooks BUSINESS tenants. This is a
# general double-entry trading/services COA with GST and AR/AP readiness.
# Business-type variants (retail, trading, services, professional) are a later
# Phase 1 follow-up; this base list is intentionally broad but neutral.
#
# Canonical platform account-code standard: 5-digit C-SS-NNN where the first
# digit is the account class (1 Asset, 2 Liability, 3 Equity, 4 Income,
# 5 Expense), the next two digits are the subclass, and the final two digits
# are the specific account. This matches the MandirMitra scheme so the whole
# platform shares one numbering SOP.
DEFAULT_BUSINESS_CHART_OF_ACCOUNTS = [
    # Assets (1xxxx) -----------------------------------------------------------
    # 11xxx Cash and bank
    _default_account("11001", "Cash in Hand", "asset", "real", is_cash_bank=True),
    _default_account("11002", "Petty Cash", "asset", "real", is_cash_bank=True),
    _default_account("11010", "Bank Account", "asset", "real", is_cash_bank=True),
    # 12xxx Receivables
    _default_account("12001", "Sundry Debtors", "asset", "personal", is_receivable=True),
    _default_account("12002", "Other Receivables", "asset", "personal", is_receivable=True),
    # 13xxx Inventory and advances
    _default_account("13001", "Inventory / Stock in Hand", "asset", "real"),
    _default_account("13002", "Advance to Suppliers", "asset", "personal"),
    # 14xxx Tax assets (Input GST)
    _default_account("14001", "Input CGST", "asset", "personal"),
    _default_account("14002", "Input SGST", "asset", "personal"),
    _default_account("14003", "Input IGST", "asset", "personal"),
    _default_account("14004", "ITC Reversed - Rule 37 (Recoverable)", "asset", "personal"),
    # 15xxx Other current assets
    _default_account("15001", "Prepaid Expenses", "asset", "real"),
    _default_account("15002", "Security Deposits Paid", "asset", "real"),
    # 16xxx Fixed assets
    _default_account("16001", "Furniture and Fixtures", "asset", "real"),
    _default_account("16002", "Office Equipment", "asset", "real"),
    _default_account("16003", "Plant and Machinery", "asset", "real"),
    _default_account("16004", "Computers", "asset", "real"),
    # Contra-asset: credited by the periodic depreciation run.
    _default_account("16099", "Accumulated Depreciation", "asset", "real"),
    # Liabilities (2xxxx) ------------------------------------------------------
    # 21xxx Payables
    _default_account("21001", "Sundry Creditors", "liability", "personal", is_payable=True),
    _default_account("21002", "Expenses Payable", "liability", "personal", is_payable=True),
    # Net salary owed to employees until the bank disbursal clears it (HR add-on).
    _default_account("21003", "Salaries Payable", "liability", "personal", is_payable=True),
    # 22xxx Tax payable (Output GST)
    _default_account("22001", "Output CGST", "liability", "personal"),
    _default_account("22002", "Output SGST", "liability", "personal"),
    _default_account("22003", "Output IGST", "liability", "personal"),
    _default_account("22004", "GST Payable (Net)", "liability", "personal", is_payable=True),
    # Reverse-charge liability — payable in CASH only (no ITC set-off).
    _default_account("22005", "GST Payable under RCM", "liability", "personal", is_payable=True),
    # 23xxx Statutory dues
    _default_account("23001", "TDS Payable", "liability", "personal", is_payable=True),
    _default_account("23002", "Statutory Dues Payable", "liability", "personal", is_payable=True),
    _default_account("23003", "Interest Payable on GST", "liability", "personal", is_payable=True),
    _default_account("23004", "TCS Payable", "liability", "personal", is_payable=True),
    # Payroll statutory dues (HR add-on). Each accrues on a payroll run and is
    # discharged when the challan/return is paid.
    _default_account("23005", "EPF Payable", "liability", "personal", is_payable=True),
    _default_account("23006", "ESI Payable", "liability", "personal", is_payable=True),
    _default_account("23007", "Professional Tax Payable", "liability", "personal", is_payable=True),
    _default_account("23008", "TDS Payable (Salary)", "liability", "personal", is_payable=True),
    # 24xxx Advances and loans
    _default_account("24001", "Advance from Customers", "liability", "personal"),
    _default_account("24002", "Loans Payable", "liability", "personal"),
    _default_account("24003", "Bank Overdraft", "liability", "personal"),
    # Equity (3xxxx) -----------------------------------------------------------
    _default_account("31001", "Owner's Capital", "equity", "nominal"),
    _default_account("31002", "Drawings", "equity", "nominal"),
    _default_account("31003", "Retained Earnings", "equity", "nominal"),
    _default_account("31004", "Opening Balance Equity", "equity", "nominal"),
    # Income (4xxxx) -----------------------------------------------------------
    # 41xxx Operating income
    _default_account("41001", "Sales", "income", "nominal"),
    _default_account("41002", "Service Income", "income", "nominal"),
    _default_account("41003", "Other Operating Income", "income", "nominal"),
    # 42xxx Other income
    _default_account("42001", "Interest Income", "income", "nominal"),
    _default_account("42002", "Discount Received", "income", "nominal"),
    _default_account("42003", "Miscellaneous Income", "income", "nominal"),
    # Expenses (5xxxx) ---------------------------------------------------------
    # 51xxx Cost of goods / purchases
    _default_account("51001", "Purchases", "expense", "nominal"),
    _default_account("51002", "Cost of Goods Sold", "expense", "nominal"),
    # 52xxx Personnel
    _default_account("52001", "Salaries and Wages", "expense", "nominal"),
    # Employer-side EPF/ESI contribution cost (HR add-on).
    _default_account("52002", "Employer Statutory Contributions", "expense", "nominal"),
    # 53xxx Operating expenses
    _default_account("53001", "Rent Expense", "expense", "nominal"),
    _default_account("53002", "Electricity Expense", "expense", "nominal"),
    _default_account("53003", "Telephone and Internet Expense", "expense", "nominal"),
    _default_account("53004", "Office Expense", "expense", "nominal"),
    _default_account("53005", "Repairs and Maintenance Expense", "expense", "nominal"),
    _default_account("53006", "Travel and Conveyance Expense", "expense", "nominal"),
    _default_account("53007", "Printing and Stationery Expense", "expense", "nominal"),
    _default_account("53008", "Advertising and Marketing Expense", "expense", "nominal"),
    _default_account("53009", "Freight and Transportation Expense", "expense", "nominal"),
    _default_account("53010", "Insurance Expense", "expense", "nominal"),
    # 54xxx Financial and other expenses
    _default_account("54001", "Bank Charges", "expense", "nominal"),
    _default_account("54002", "Legal and Professional Fees", "expense", "nominal"),
    _default_account("54003", "Depreciation Expense", "expense", "nominal"),
    _default_account("54004", "Discount Allowed", "expense", "nominal"),
    _default_account("54005", "Miscellaneous Expense", "expense", "nominal"),
    _default_account("54006", "Interest on GST", "expense", "nominal"),
    # Composition levy is the dealer's own cost (it is never collected from buyers).
    _default_account("54007", "GST Expense (Composition)", "expense", "nominal"),
]


def get_default_chart_of_accounts(organization_type: str | None = None) -> list[dict]:
    """Return the default COA template for an organization type.

    BUSINESS (and the MitraBooks business app) uses the general business COA.
    Every other organization type keeps the existing housing-style template so
    that live HOUSING/TEMPLE behavior is unchanged.
    """
    normalized = str(organization_type or "").strip().upper()
    if normalized == "BUSINESS":
        return DEFAULT_BUSINESS_CHART_OF_ACCOUNTS
    return DEFAULT_HOUSING_CHART_OF_ACCOUNTS

async def create_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
    code: str | None,
    name: str,
    account_type: str,
    classification: str,
    is_cash_bank: bool,
    is_receivable: bool,
    is_payable: bool,
) -> Account:
    account = Account(
        app_key=app_key,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        code=code,
        name=name,
        type=account_type,
        classification=classification,
        is_cash_bank=is_cash_bank,
        is_receivable=is_receivable,
        is_payable=is_payable,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


async def list_accounts(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str = "mandirmitra",
    accounting_entity_id: str = "primary",
) -> list[Account]:
    stmt: Select[tuple[Account]] = (
        select(Account)
        .where(*_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id))
        .order_by(Account.name.asc())
    )
    rows = await session.execute(stmt)
    return list(rows.scalars().all())


async def update_account(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    code: str,
    name: str,
) -> Account:
    normalized_code = str(code or "").strip()
    normalized_name = str(name or "").strip()
    if not normalized_code:
        raise AccountingValidationError("Account code is required")
    if len(normalized_name) < 2:
        raise AccountingValidationError("Account name must be at least 2 characters")

    stmt = select(Account).where(
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        Account.code == normalized_code,
    )
    account = (await session.execute(stmt)).scalar_one_or_none()
    if account is None:
        raise AccountingNotFoundError("Account not found")

    account.name = normalized_name
    await session.commit()
    await session.refresh(account)
    return account


async def initialize_default_chart_of_accounts(
    session: AsyncSession,
    *,
    tenant_id: str,
    app_key: str,
    accounting_entity_id: str = "primary",
    organization_type: str | None = None,
) -> dict:
    existing_stmt = select(Account.code).where(
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id),
        Account.code.is_not(None),
    )
    existing_codes = set((await session.execute(existing_stmt)).scalars().all())

    chart_of_accounts = get_default_chart_of_accounts(organization_type)

    created = 0
    for item in chart_of_accounts:
        if item["code"] in existing_codes:
            continue
        session.add(
            Account(
                app_key=app_key,
                tenant_id=tenant_id,
                accounting_entity_id=accounting_entity_id,
                code=item["code"],
                name=item["name"],
                type=item["account_type"],
                classification=item["classification"],
                is_cash_bank=item["is_cash_bank"],
                is_receivable=item["is_receivable"],
                is_payable=item["is_payable"],
            )
        )
        created += 1

    if created:
        await session.commit()

    total_stmt = select(func.count()).select_from(Account).where(
        *_accounting_scope(Account, app_key=app_key, tenant_id=tenant_id, accounting_entity_id=accounting_entity_id)
    )
    total = int((await session.execute(total_stmt)).scalar_one())
    return {
        "accounts_created": created,
        "accounts_existing": len(existing_codes),
        "total_accounts": total,
    }


