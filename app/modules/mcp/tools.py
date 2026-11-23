"""Read-only MCP tool catalogue for MitraBooks.

Each tool maps to one existing GET route. Arguments become query parameters or
path segments; nothing else of the client's input reaches the route. The tool
descriptions are written for any model, not one vendor's, since this server is
meant for every MCP client.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_DATE = {"type": "string", "format": "date", "description": "Date as YYYY-MM-DD."}
_KIND = {
    "type": "string",
    "enum": ["receivable", "payable"],
    "description": "receivable = customers (AR); payable = vendors (AP). Default receivable.",
}
_PERIOD = {
    "type": "string",
    "pattern": r"^\d{4}-(0[1-9]|1[0-2])$",
    "description": "Tax period month as YYYY-MM, e.g. 2026-09.",
}
_QUARTER = {
    "type": "string",
    "pattern": r"^\d{4}-Q[1-4]$",
    "description": "Indian financial-year quarter as YYYY-Qn where YYYY is the FY start year; Q1 = Apr-Jun. e.g. 2026-Q2 = Jul-Sep 2026.",
}
_ENTITY = {
    "type": "string",
    "description": "Accounting entity (set of books) id. Omit for the default 'primary' books.",
}
_UUID_RE = r"^[A-Za-z0-9][A-Za-z0-9_\-]{0,79}$"


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    path: str
    properties: dict[str, dict] = field(default_factory=dict)
    required: tuple[str, ...] = ()
    path_params: tuple[str, ...] = ()
    fixed_query: dict[str, Any] = field(default_factory=dict)

    def input_schema(self) -> dict:
        props = {**self.properties, "accounting_entity_id": _ENTITY}
        schema: dict[str, Any] = {"type": "object", "properties": props, "additionalProperties": False}
        if self.required:
            schema["required"] = list(self.required)
        return schema

    def descriptor(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema(),
            "annotations": {
                "title": self.title,
                "readOnlyHint": True,
                "destructiveHint": False,
                "idempotentHint": True,
                "openWorldHint": False,
            },
        }


TOOLS: tuple[Tool, ...] = (
    # ---- Core ledger -------------------------------------------------------
    Tool(
        name="list_accounts",
        title="Chart of accounts",
        description="List the chart of accounts: id, code, name, type, and flags such as cash/bank, receivable, payable. Use the id with get_account_ledger.",
        path="/api/v1/accounting/accounts",
    ),
    Tool(
        name="get_trial_balance",
        title="Trial balance",
        description="Trial balance as of a date: debit and credit balance per account, totals, and whether the books balance.",
        path="/api/v1/accounting/reports/trial-balance",
        properties={"as_of": _DATE},
        required=("as_of",),
    ),
    Tool(
        name="get_profit_and_loss",
        title="Profit and loss",
        description="Profit and loss (income statement) for a date range: income and expense accounts and net profit.",
        path="/api/v1/accounting/reports/pnl",
        properties={"from_date": _DATE, "to_date": _DATE},
        required=("from_date", "to_date"),
    ),
    Tool(
        name="get_balance_sheet",
        title="Balance sheet",
        description="Balance sheet as of a date: assets, liabilities and equity.",
        path="/api/v1/accounting/reports/balance-sheet",
        properties={"as_of": _DATE},
        required=("as_of",),
    ),
    Tool(
        name="get_account_ledger",
        title="Account ledger",
        description="All posted ledger lines for one account (general ledger for that account). Get account ids from list_accounts.",
        path="/api/v1/accounting/ledger/{account_id}",
        properties={"account_id": {"type": "integer", "minimum": 1, "description": "Account id from list_accounts."}},
        required=("account_id",),
        path_params=("account_id",),
    ),
    Tool(
        name="list_journal_entries",
        title="Journal entries",
        description="List posted journal entries, newest first, optionally within a date range. Paginate with limit/offset.",
        path="/api/v1/accounting/journal",
        properties={
            "from_date": _DATE,
            "to_date": _DATE,
            "limit": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Default 100."},
            "offset": {"type": "integer", "minimum": 0},
        },
    ),
    Tool(
        name="get_journal_entry",
        title="Journal entry detail",
        description="One journal entry with all its debit/credit lines.",
        path="/api/v1/accounting/journal/{journal_id}",
        properties={"journal_id": {"type": "integer", "minimum": 1}},
        required=("journal_id",),
        path_params=("journal_id",),
    ),
    # ---- Parties, receivables, payables -----------------------------------
    Tool(
        name="list_parties",
        title="Customers and vendors",
        description="List customers and vendors (parties) with GSTIN and contact details. party_id from here is used by the statement and aging tools.",
        path="/api/v1/business/parties",
        properties={
            "party_type": {"type": "string", "enum": ["customer", "vendor", "both"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
        },
    ),
    Tool(
        name="get_party_statement",
        title="Party statement of account",
        description="Statement of account for one customer or vendor: opening balance, invoices, payments and running balance for a date range.",
        path="/api/v1/business/statements/{party_id}",
        properties={
            "party_id": {"type": "string", "pattern": _UUID_RE},
            "kind": _KIND,
            "from_date": _DATE,
            "to_date": _DATE,
        },
        required=("party_id",),
        path_params=("party_id",),
    ),
    Tool(
        name="get_aging_report",
        title="AR/AP aging",
        description="Receivables or payables aging by days past due (buckets 0-30 incl. not yet due, 31-60, 61-90, 90+) per party, optionally for one party.",
        path="/api/v1/business/allocations/aging",
        properties={"kind": _KIND, "party_id": {"type": "string", "pattern": _UUID_RE}, "as_of": _DATE},
    ),
    Tool(
        name="list_open_items",
        title="Open invoices and bills",
        description="Unsettled invoices (receivable) or bills (payable) with outstanding amounts and due dates.",
        path="/api/v1/business/allocations/open-items",
        properties={
            "kind": _KIND,
            "party_id": {"type": "string", "pattern": _UUID_RE},
            "as_of": _DATE,
            "include_settled": {"type": "boolean"},
        },
    ),
    Tool(
        name="list_unallocated_payments",
        title="Unallocated payments",
        description="Receipts or payments not yet matched to invoices or bills - a common month-end clean-up item.",
        path="/api/v1/business/allocations/unallocated-payments",
        properties={"kind": _KIND, "party_id": {"type": "string", "pattern": _UUID_RE}},
    ),
    # ---- GST and TDS (India) ----------------------------------------------
    Tool(
        name="get_gstr3b",
        title="GSTR-3B summary",
        description="GSTR-3B monthly summary return computed from the books: outward supplies and tax (3.1), eligible ITC (4), and tax payable (6.1), plus GSTN-format JSON.",
        path="/api/v1/business/returns/gstr-3b",
        properties={"period": _PERIOD},
        required=("period",),
    ),
    Tool(
        name="get_gstr1",
        title="GSTR-1 outward supplies",
        description="GSTR-1 for a month: B2B, B2CL, B2CS, credit/debit notes, HSN summary and document summary, plus GSTN-format JSON.",
        path="/api/v1/business/returns/gstr-1",
        properties={"period": _PERIOD},
        required=("period",),
    ),
    Tool(
        name="get_cmp08",
        title="CMP-08 (composition)",
        description="CMP-08 quarterly statement for a composition-scheme dealer: turnover and tax payable.",
        path="/api/v1/business/returns/cmp-08",
        properties={"quarter": _QUARTER},
        required=("quarter",),
    ),
    Tool(
        name="get_gstr4",
        title="GSTR-4 (composition annual)",
        description="GSTR-4 annual return for a composition-scheme dealer.",
        path="/api/v1/business/returns/gstr-4",
        properties={
            "financial_year": {
                "type": "string",
                "pattern": r"^\d{4}-\d{2}$",
                "description": "Indian financial year as YYYY-YY, e.g. 2026-27.",
            }
        },
        required=("financial_year",),
    ),
    Tool(
        name="get_tds_register",
        title="TDS register",
        description="TDS deducted in a quarter by section and deductee, for 26Q/24Q preparation.",
        path="/api/v1/business/tds/register",
        properties={"quarter": _QUARTER},
        required=("quarter",),
    ),
    # ---- Banking ----------------------------------------------------------
    Tool(
        name="get_bank_reconciliation",
        title="Bank reconciliation",
        description="Bank reconciliation for one bank account: book balance, statement balance, matched lines and unreconciled items on both sides.",
        path="/api/v1/business/bank-recon",
        properties={
            "account_id": {"type": "integer", "minimum": 1, "description": "Bank account id from list_accounts."},
            "as_of": _DATE,
        },
        required=("account_id",),
    ),
    Tool(
        name="get_cash_bank_book",
        title="Cash and bank book",
        description="Cash book and/or bank book for a date range with opening balance, receipts, payments and closing balance.",
        path="/api/v1/business/banking/books",
        properties={
            "from_date": _DATE,
            "to_date": _DATE,
            "book_type": {"type": "string", "enum": ["all", "cash", "bank"]},
        },
        required=("from_date", "to_date"),
    ),
    # ---- Health and analytics ---------------------------------------------
    Tool(
        name="get_dashboard",
        title="Business dashboard",
        description="Headline numbers for the financial year to date, as shown on the MitraBooks home dashboard.",
        path="/api/v1/business/dashboard",
        properties={"as_of": _DATE},
    ),
    Tool(
        name="get_mis_kpis",
        title="MIS KPIs",
        description="Management (MIS) KPIs: receivable and payable totals and overdue amounts, top outstanding parties, and month-wise sales vs purchases.",
        path="/api/v1/business/mis/kpis",
        properties={"as_of": _DATE},
    ),
    Tool(
        name="get_financial_health",
        title="Financial health score",
        description="Financial health score with liquidity, solvency, profitability and efficiency ratios and the factors behind them.",
        path="/api/v1/business/financial-health",
        properties={"as_of": _DATE},
        fixed_query={"narrate": "false"},
    ),
    Tool(
        name="get_cash_flow_forecast",
        title="Cash flow forecast",
        description="Cash flow forecast with monthly projection, burn rate and runway.",
        path="/api/v1/business/cash-flow-forecast",
        properties={"as_of": _DATE, "horizon_months": {"type": "integer", "minimum": 1, "maximum": 24}},
        fixed_query={"narrate": "false"},
    ),
    Tool(
        name="get_data_health",
        title="Books data-health check",
        description="Data health score for a book review: rule-by-rule checks with evidence on draft or stuck documents, party data, bank reconciliation and open items - issues to fix before closing a month.",
        path="/api/v1/business/data-health",
        properties={"as_of": _DATE},
    ),
    Tool(
        name="list_pending_approvals",
        title="Approval queue",
        description="Vouchers, invoices and bills waiting for approval or still in draft. Needs a tenant admin.",
        path="/api/v1/business/approval-queue",
        properties={
            "document_type": {
                "type": "string",
                "enum": ["voucher", "sales_invoice", "purchase_bill", "credit_note", "debit_note"],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
        },
    ),
)

TOOLS_BY_NAME: dict[str, Tool] = {tool.name: tool for tool in TOOLS}

_PATH_SEGMENT_RE = re.compile(_UUID_RE)


class ToolArgumentError(ValueError):
    pass


def build_request(tool: Tool, arguments: dict[str, Any] | None) -> tuple[str, dict[str, str]]:
    """Turn tool arguments into (path, query) for the underlying GET route.

    Only declared properties are used. Path segments are type- and pattern-checked
    here so a crafted value can never point the call at a different route; all
    other values are validated again by the route itself.
    """
    args = dict(arguments or {})
    allowed = set(tool.properties) | {"accounting_entity_id"}
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise ToolArgumentError(f"Unknown argument(s): {', '.join(unknown)}")
    missing = [name for name in tool.required if args.get(name) in (None, "")]
    if missing:
        raise ToolArgumentError(f"Missing required argument(s): {', '.join(missing)}")

    path = tool.path
    for name in tool.path_params:
        value = args.pop(name)
        if tool.properties[name].get("type") == "integer":
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ToolArgumentError(f"{name} must be a positive integer")
            segment = str(value)
        else:
            segment = str(value)
            if not _PATH_SEGMENT_RE.match(segment):
                raise ToolArgumentError(f"{name} has an invalid format")
        path = path.replace("{" + name + "}", segment)

    query: dict[str, str] = {}
    for name, value in args.items():
        if value is None:
            continue
        if isinstance(value, bool):
            query[name] = "true" if value else "false"
        elif isinstance(value, (str, int, float)):
            query[name] = str(value)
        else:
            raise ToolArgumentError(f"{name} must be a plain value")
    query.update(tool.fixed_query)
    return path, query
