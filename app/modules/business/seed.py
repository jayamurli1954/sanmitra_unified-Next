from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.schemas import JournalLineIn, JournalPostRequest
from app.accounting.service import (
    get_accounts_payable,
    get_accounts_receivable,
    get_profit_loss,
    get_receipts_payments,
    get_trial_balance,
    initialize_default_chart_of_accounts,
    list_accounts,
    post_journal_entry,
)
from app.modules.business import service as business_service
from app.modules.business.schemas import PartyCreateRequest, TypedVoucherCreateRequest

APP_KEY = "mitrabooks"
ACCOUNTING_ENTITY_ID = "primary"
SEED_DATE = date(2026, 6, 1)


async def _party_by_code(
    *,
    tenant_id: str,
    accounting_entity_id: str,
    party_code: str,
) -> dict[str, Any] | None:
    row = await business_service.get_collection(business_service.PARTIES_COLLECTION).find_one(
        {
            "tenant_id": tenant_id,
            "app_key": APP_KEY,
            "accounting_entity_id": accounting_entity_id,
            "party_code": party_code,
            "is_active": True,
        }
    )
    return business_service._json_safe_doc(row) if row else None


async def _ensure_party(
    *,
    tenant_id: str,
    accounting_entity_id: str,
    created_by: str,
    payload: PartyCreateRequest,
) -> dict[str, Any]:
    existing = await _party_by_code(
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        party_code=str(payload.party_code or ""),
    )
    if existing is not None:
        return {**existing, "created": False}

    created = await business_service.create_party(
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=payload,
    )
    return {**created, "created": True}


def _account_id_by_code(accounts, code: str) -> int:
    for account in accounts:
        if account.code == code:
            return int(account.id)
    raise RuntimeError(f"MitraBooks seed account code missing: {code}")


async def _post_seed_journal(
    session: AsyncSession,
    *,
    tenant_id: str,
    accounting_entity_id: str,
    created_by: str,
    reference: str,
    description: str,
    source_document_type: str,
    source_document_id: str,
    lines: list[JournalLineIn],
) -> bool:
    _entry, created = await post_journal_entry(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        payload=JournalPostRequest(
            entry_date=SEED_DATE,
            description=description,
            reference=reference,
            source_module="mitrabooks_e2e_seed",
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            lines=lines,
        ),
        idempotency_key=f"mitrabooks-e2e:{source_document_id.lower()}",
    )
    return created


async def _post_seed_voucher(
    session: AsyncSession,
    *,
    tenant_id: str,
    created_by: str,
    voucher_type: str,
    reference: str,
    amount: Decimal,
    debit_account_id: int,
    credit_account_id: int,
    description: str,
    party_id: str | None = None,
) -> bool:
    doc = await business_service.post_typed_voucher(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        created_by=created_by,
        payload=TypedVoucherCreateRequest(
            voucher_type=voucher_type,
            entry_date=SEED_DATE,
            amount=amount,
            debit_account_id=debit_account_id,
            credit_account_id=credit_account_id,
            description=description,
            reference=reference,
            party_id=party_id,
            accounting_entity_id=ACCOUNTING_ENTITY_ID,
        ),
        idempotency_key=f"mitrabooks-e2e:{reference.lower()}",
    )
    return bool(doc.get("created"))


async def ensure_mitrabooks_e2e_seed(
    session: AsyncSession,
    *,
    tenant_id: str,
    created_by: str,
    accounting_entity_id: str = ACCOUNTING_ENTITY_ID,
) -> dict[str, Any]:
    """Seed a BUSINESS tenant with practical MitraBooks E2E accounting data.

    This is deliberately idempotent and scoped to the MitraBooks app context.
    It seeds accounting/report readiness; sales and purchase invoice domain
    modules remain future work and are represented here as GL source documents.
    """
    await business_service.ensure_business_indexes()
    coa_result = await initialize_default_chart_of_accounts(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        organization_type="BUSINESS",
    )
    accounts = await list_accounts(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
    )
    account_ids = {code: _account_id_by_code(accounts, code) for code in {
        "11001",
        "11010",
        "12001",
        "14001",
        "14002",
        "21001",
        "22001",
        "22002",
        "31001",
        "41001",
        "51001",
        "53004",
        "54001",
    }}

    parties = [
        await _ensure_party(
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            payload=PartyCreateRequest(
                party_name="Acme Retail Pvt Ltd",
                party_type="customer",
                party_code="CUST-ACME",
                gstin="29ABCDE1234F1Z5",
                email="accounts@acmeretail.local",
                billing_address="Bengaluru, Karnataka",
            ),
        ),
        await _ensure_party(
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            payload=PartyCreateRequest(
                party_name="Jayam Publications",
                party_type="customer",
                party_code="CUST-JAYAM",
                gstin="29ABCDE2345F1Z6",
                email="billing@jayam.local",
                billing_address="Mysuru, Karnataka",
            ),
        ),
        await _ensure_party(
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            payload=PartyCreateRequest(
                party_name="Karnataka Office Supplies",
                party_type="vendor",
                party_code="VEND-OFFICE",
                gstin="29ABCDE3456F1Z7",
                email="billing@office-supplies.local",
                billing_address="Bengaluru, Karnataka",
            ),
        ),
        await _ensure_party(
            tenant_id=tenant_id,
            accounting_entity_id=accounting_entity_id,
            created_by=created_by,
            payload=PartyCreateRequest(
                party_name="Workspace Rent Services",
                party_type="vendor",
                party_code="VEND-RENT",
                gstin="29ABCDE4567F1Z8",
                email="accounts@workspace-rent.local",
                billing_address="Bengaluru, Karnataka",
            ),
        ),
    ]
    party_by_code = {party["party_code"]: party for party in parties}

    journals_created = 0
    vouchers_created = 0

    vouchers_created += await _post_seed_voucher(
        session,
        tenant_id=tenant_id,
        created_by=created_by,
        voucher_type="journal",
        reference="E2E-OPENING-BANK",
        amount=Decimal("500000.00"),
        debit_account_id=account_ids["11010"],
        credit_account_id=account_ids["31001"],
        description="E2E opening bank balance against owner capital",
    )
    journals_created += await _post_seed_journal(
        session,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        reference="E2E-SINV-001",
        description="E2E sales invoice with output GST",
        source_document_type="sales_invoice",
        source_document_id="E2E-SINV-001",
        lines=[
            JournalLineIn(account_id=account_ids["12001"], debit=Decimal("118000.00"), credit=Decimal("0.00")),
            JournalLineIn(account_id=account_ids["41001"], debit=Decimal("0.00"), credit=Decimal("100000.00")),
            JournalLineIn(account_id=account_ids["22001"], debit=Decimal("0.00"), credit=Decimal("9000.00")),
            JournalLineIn(account_id=account_ids["22002"], debit=Decimal("0.00"), credit=Decimal("9000.00")),
        ],
    )
    journals_created += await _post_seed_journal(
        session,
        tenant_id=tenant_id,
        accounting_entity_id=accounting_entity_id,
        created_by=created_by,
        reference="E2E-PUR-001",
        description="E2E purchase invoice with input GST",
        source_document_type="purchase_invoice",
        source_document_id="E2E-PUR-001",
        lines=[
            JournalLineIn(account_id=account_ids["51001"], debit=Decimal("50000.00"), credit=Decimal("0.00")),
            JournalLineIn(account_id=account_ids["14001"], debit=Decimal("4500.00"), credit=Decimal("0.00")),
            JournalLineIn(account_id=account_ids["14002"], debit=Decimal("4500.00"), credit=Decimal("0.00")),
            JournalLineIn(account_id=account_ids["21001"], debit=Decimal("0.00"), credit=Decimal("59000.00")),
        ],
    )
    vouchers_created += await _post_seed_voucher(
        session,
        tenant_id=tenant_id,
        created_by=created_by,
        voucher_type="receipt",
        reference="E2E-REC-001",
        amount=Decimal("30000.00"),
        debit_account_id=account_ids["11010"],
        credit_account_id=account_ids["12001"],
        description="E2E customer receipt against sales invoice",
        party_id=party_by_code["CUST-ACME"]["party_id"],
    )
    vouchers_created += await _post_seed_voucher(
        session,
        tenant_id=tenant_id,
        created_by=created_by,
        voucher_type="payment",
        reference="E2E-PAY-001",
        amount=Decimal("20000.00"),
        debit_account_id=account_ids["21001"],
        credit_account_id=account_ids["11010"],
        description="E2E vendor payment against purchase invoice",
        party_id=party_by_code["VEND-OFFICE"]["party_id"],
    )
    vouchers_created += await _post_seed_voucher(
        session,
        tenant_id=tenant_id,
        created_by=created_by,
        voucher_type="payment",
        reference="E2E-EXP-001",
        amount=Decimal("12000.00"),
        debit_account_id=account_ids["53004"],
        credit_account_id=account_ids["11010"],
        description="E2E office expense paid from bank",
        party_id=party_by_code["VEND-RENT"]["party_id"],
    )
    vouchers_created += await _post_seed_voucher(
        session,
        tenant_id=tenant_id,
        created_by=created_by,
        voucher_type="payment",
        reference="E2E-BANK-CHG-001",
        amount=Decimal("350.00"),
        debit_account_id=account_ids["54001"],
        credit_account_id=account_ids["11010"],
        description="E2E bank charges entry",
    )
    vouchers_created += await _post_seed_voucher(
        session,
        tenant_id=tenant_id,
        created_by=created_by,
        voucher_type="contra",
        reference="E2E-CONTRA-001",
        amount=Decimal("5000.00"),
        debit_account_id=account_ids["11001"],
        credit_account_id=account_ids["11010"],
        description="E2E bank to cash contra entry",
    )

    trial_lines, trial_debit, trial_credit = await get_trial_balance(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        as_of=SEED_DATE,
    )
    _pnl_lines, income_total, expense_total, net_profit = await get_profit_loss(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        from_date=SEED_DATE,
        to_date=SEED_DATE,
    )
    _rp_lines, total_receipts, total_payments, net_receipts = await get_receipts_payments(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        from_date=SEED_DATE,
        to_date=SEED_DATE,
    )
    _ar_lines, ar_total = await get_accounts_receivable(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        as_of=SEED_DATE,
    )
    _ap_lines, ap_total = await get_accounts_payable(
        session,
        tenant_id=tenant_id,
        app_key=APP_KEY,
        accounting_entity_id=accounting_entity_id,
        as_of=SEED_DATE,
    )

    return {
        "tenant_id": tenant_id,
        "app_key": APP_KEY,
        "accounting_entity_id": accounting_entity_id,
        "seed_date": SEED_DATE.isoformat(),
        "chart_of_accounts": coa_result,
        "parties_total": len(parties),
        "parties_created": sum(1 for party in parties if party.get("created")),
        "journals_created": journals_created,
        "vouchers_created": vouchers_created,
        "trial_balance": {
            "line_count": len(trial_lines),
            "total_debit": str(trial_debit),
            "total_credit": str(trial_credit),
            "balanced": trial_debit == trial_credit,
        },
        "profit_loss": {
            "income_total": str(income_total),
            "expense_total": str(expense_total),
            "net_profit": str(net_profit),
        },
        "receipts_payments": {
            "total_receipts": str(total_receipts),
            "total_payments": str(total_payments),
            "net_receipts": str(net_receipts),
        },
        "receivables_total": str(ar_total),
        "payables_total": str(ap_total),
        "gap_note": "Sales invoice, purchase invoice, and GST return domain workflows are not yet implemented; seed uses GL source documents for report-ready E2E data.",
    }
