from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


AccountType = Literal["asset", "liability", "equity", "income", "expense"]
AccountClassification = Literal["personal", "real", "nominal"]
SourceSystem = Literal[
    "ghar_mitra",
    "mandir_mitra",
    "mitra_books",
    "legal_mitra",
    "invest_mitra",
    "tally",
    "zoho",
    "csv",
]
MappingStatus = Literal["active", "draft", "inactive"]
LegacyCoaDecisionAction = Literal["mapped_to_existing", "created_then_mapped"]


class AccountCreateRequest(BaseModel):
    code: str | None = Field(default=None, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    type: AccountType
    classification: AccountClassification
    is_cash_bank: bool = False
    is_receivable: bool = False
    is_payable: bool = False


class AccountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)


class AccountResponse(BaseModel):
    id: int
    code: str | None
    name: str
    type: AccountType
    classification: AccountClassification
    is_cash_bank: bool
    is_receivable: bool
    is_payable: bool


class ChartOfAccountsInitializeResponse(BaseModel):
    accounts_created: int
    accounts_existing: int
    total_accounts: int


class JournalLineIn(BaseModel):
    account_id: int
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    # Optional sub-ledger party (customer/vendor) for receivable/payable lines.
    party_id: str | None = Field(default=None, max_length=64)
    # Optional cost-centre dimension (enterprise add-on). Tags the line to a
    # cost centre for departmental/branch P&L and budget-vs-actual reporting.
    cost_center_id: str | None = Field(default=None, max_length=64)

    @field_validator("debit", "credit")
    @classmethod
    def validate_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Amount cannot be negative")
        return value


class JournalPostRequest(BaseModel):
    entry_date: date
    description: str | None = None
    reference: str | None = Field(default=None, max_length=120)
    source_module: str | None = Field(default=None, max_length=50)
    source_document_type: str | None = Field(default=None, max_length=80)
    source_document_id: str | None = Field(default=None, max_length=120)
    lines: list[JournalLineIn] = Field(min_length=2)


class JournalPostResponse(BaseModel):
    id: int
    tenant_id: str
    created: bool
    total_debit: Decimal
    total_credit: Decimal


class JournalReversalRequest(BaseModel):
    entry_date: date | None = None
    reason: str | None = Field(default=None, max_length=300)


class JournalReversalResponse(BaseModel):
    id: int
    original_journal_id: int
    tenant_id: str
    created: bool
    total_debit: Decimal
    total_credit: Decimal


class JournalLineResponse(BaseModel):
    id: int
    account_id: int
    debit: Decimal
    credit: Decimal


class JournalEntryResponse(BaseModel):
    id: int
    tenant_id: str
    app_key: str
    accounting_entity_id: str
    entry_date: date
    description: str | None
    reference: str | None
    source_module: str | None
    source_document_type: str | None
    source_document_id: str | None
    reversal_of_journal_id: int | None
    idempotency_key: str | None
    total_debit: Decimal
    total_credit: Decimal
    created_by: str | None
    lines: list[JournalLineResponse]


class LedgerLineResponse(BaseModel):
    journal_id: int
    entry_date: date
    reference: str | None
    description: str | None
    debit: Decimal
    credit: Decimal
    running_balance: Decimal


class TrialBalanceLineResponse(BaseModel):
    account_id: int
    account_code: str | None = None
    account_name: str
    debit_total: Decimal
    credit_total: Decimal
    net_balance: Decimal


class TrialBalanceResponse(BaseModel):
    as_of: date
    lines: list[TrialBalanceLineResponse]
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool


class ProfitLossLineResponse(BaseModel):
    account_id: int
    account_code: str | None = None
    account_name: str
    account_type: AccountType
    debit_total: Decimal
    credit_total: Decimal
    net_amount: Decimal


class ProfitLossResponse(BaseModel):
    from_date: date
    to_date: date
    income_total: Decimal
    expense_total: Decimal
    net_profit: Decimal
    lines: list[ProfitLossLineResponse]


class ReceiptsPaymentsLineResponse(BaseModel):
    account_id: int
    account_code: str | None = None
    account_name: str
    receipts: Decimal
    payments: Decimal
    net_receipts: Decimal


class ReceiptsPaymentsResponse(BaseModel):
    from_date: date
    to_date: date
    total_receipts: Decimal
    total_payments: Decimal
    net_receipts: Decimal
    lines: list[ReceiptsPaymentsLineResponse]


class BalanceSheetLineResponse(BaseModel):
    account_id: int
    account_code: str | None = None
    account_name: str
    balance: Decimal


class BalanceSheetResponse(BaseModel):
    as_of: date
    assets: list[BalanceSheetLineResponse]
    liabilities: list[BalanceSheetLineResponse]
    equity: list[BalanceSheetLineResponse]
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    balanced: bool


class ARApLineResponse(BaseModel):
    account_id: int
    account_name: str
    balance: Decimal


class ARApResponse(BaseModel):
    as_of: date
    total_balance: Decimal
    lines: list[ARApLineResponse]


class CoaSourceAccountIn(BaseModel):
    source_system: SourceSystem
    source_account_code: str = Field(min_length=1, max_length=50)
    source_account_name: str = Field(min_length=1, max_length=200)
    source_account_type: AccountType | None = None


class CoaSourceAccountBulkUpsertRequest(BaseModel):
    items: list[CoaSourceAccountIn] = Field(min_length=1)


class CoaSourceAccountResponse(BaseModel):
    id: int
    source_system: SourceSystem
    source_account_code: str
    source_account_name: str
    source_account_type: str | None
    is_active: bool
    mapped: bool


class CoaMappingIn(BaseModel):
    source_system: SourceSystem
    source_account_code: str = Field(min_length=1, max_length=50)
    canonical_account_id: int
    status: MappingStatus = "active"
    notes: str | None = Field(default=None, max_length=1000)


class CoaMappingBulkUpsertRequest(BaseModel):
    items: list[CoaMappingIn] = Field(min_length=1)


class CoaMappingResponse(BaseModel):
    id: int
    source_system: SourceSystem
    source_account_code: str
    source_account_name: str
    canonical_account_id: int
    canonical_account_name: str
    status: MappingStatus
    notes: str | None


class CoaMappingSuggestionResponse(BaseModel):
    canonical_account_id: int | None
    canonical_account_name: str | None
    confidence: Decimal | None
    reason: str | None


class CoaMappingGapResponse(BaseModel):
    source_system: SourceSystem
    source_account_code: str
    source_account_name: str
    source_account_type: str | None
    suggestion: CoaMappingSuggestionResponse | None


class CoaOnboardingStatusResponse(BaseModel):
    source_system: SourceSystem
    total_source_accounts: int
    mapped_active: int
    mapped_draft: int
    unmapped: int


class CoaMappingApproveRequest(BaseModel):
    source_system: SourceSystem
    source_account_codes: list[str] | None = None


class CoaMappingApproveResponse(BaseModel):
    source_system: SourceSystem
    approved_count: int


class LegacyCoaImportPreviewRequest(BaseModel):
    csv: str = Field(min_length=1)
    source_system: SourceSystem = "tally"


class LegacyCoaCanonicalAccountResponse(BaseModel):
    id: int
    code: str | None = None
    name: str
    type: AccountType


class LegacyCoaPreviewRowResponse(BaseModel):
    row_number: int
    source_account_code: str
    source_account_name: str
    source_account_type: AccountType | None = None
    match_status: Literal["already_mapped", "suggested", "unmatched"]
    already_mapped: bool = False
    mapped_account_id: int | None = None
    mapped_account_code: str | None = None
    mapped_account_name: str | None = None
    suggestion: CoaMappingSuggestionResponse | None = None


class LegacyCoaImportPreviewResponse(BaseModel):
    source_system: SourceSystem
    rows: list[LegacyCoaPreviewRowResponse]
    canonical_accounts: list[LegacyCoaCanonicalAccountResponse]
    row_count: int
    suggested_count: int
    unmatched_count: int
    already_mapped_count: int
    can_confirm_suggested: bool


class LegacyCoaCreateAccountIn(BaseModel):
    code: str | None = Field(default=None, max_length=30)
    name: str = Field(min_length=2, max_length=200)
    type: AccountType
    classification: AccountClassification
    is_cash_bank: bool = False
    is_receivable: bool = False
    is_payable: bool = False


class LegacyCoaSuggestionSnapshotIn(BaseModel):
    canonical_account_id: int | None = None
    canonical_account_name: str | None = None
    confidence: Decimal | None = None
    reason: str | None = None


class LegacyCoaDecisionIn(BaseModel):
    source_account_code: str = Field(min_length=1, max_length=50)
    source_account_name: str = Field(min_length=1, max_length=200)
    source_account_type: AccountType | None = None
    action: Literal["map_existing", "create_new"]
    canonical_account_id: int | None = None
    create: LegacyCoaCreateAccountIn | None = None
    notes: str | None = Field(default=None, max_length=1000)
    suggestion: LegacyCoaSuggestionSnapshotIn | None = None


class LegacyCoaImportConfirmRequest(BaseModel):
    source_system: SourceSystem = "tally"
    decisions: list[LegacyCoaDecisionIn] = Field(min_length=1, max_length=500)


class LegacyCoaDecisionResponse(BaseModel):
    id: int
    source_system: SourceSystem
    source_account_code: str
    source_account_name: str
    action: LegacyCoaDecisionAction
    canonical_account_id: int
    canonical_account_code: str | None = None
    canonical_account_name: str
    created_account: bool
    suggested_account_id: int | None = None
    suggested_account_name: str | None = None
    suggestion_confidence: Decimal | None = None
    suggestion_reason: str | None = None
    notes: str | None = None
    decided_by: str | None = None
    decided_at: datetime
    mapping_id: int
    audit_event_id: str | None = None


class LegacyCoaImportConfirmResponse(BaseModel):
    source_system: SourceSystem
    confirmed_count: int
    created_account_count: int
    mapped_existing_count: int
    decisions: list[LegacyCoaDecisionResponse]


class SourceJournalLineIn(BaseModel):
    source_account_code: str = Field(min_length=1, max_length=50)
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    @field_validator("debit", "credit")
    @classmethod
    def validate_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Amount cannot be negative")
        return value


class SourceJournalPostRequest(BaseModel):
    source_system: SourceSystem
    entry_date: date
    description: str | None = None
    reference: str | None = Field(default=None, max_length=120)
    source_document_type: str | None = Field(default=None, max_length=80)
    source_document_id: str | None = Field(default=None, max_length=120)
    lines: list[SourceJournalLineIn] = Field(min_length=2)


class SourceJournalResolvedLineResponse(BaseModel):
    source_account_code: str
    canonical_account_id: int
    debit: Decimal
    credit: Decimal


class SourceJournalPostResponse(BaseModel):
    id: int
    tenant_id: str
    created: bool
    total_debit: Decimal
    total_credit: Decimal
    source_system: SourceSystem
    resolved_lines: list[SourceJournalResolvedLineResponse]

