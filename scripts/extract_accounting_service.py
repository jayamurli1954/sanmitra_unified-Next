"""Extract app/accounting/service.py into common/chart/coa_mapping/reports + slim facade.

Pure move per docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md §6–§8.
Posting core (validate_journal_lines, post_journal_entry, reverse_journal_entry,
cash guards, post_source_journal_entry) stays in service.py.

Run: python scripts/extract_accounting_service.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "app/accounting/service.py"
COMMON = ROOT / "app/accounting/common.py"
CHART = ROOT / "app/accounting/chart.py"
COA_MAPPING = ROOT / "app/accounting/coa_mapping.py"
REPORTS = ROOT / "app/accounting/reports/__init__.py"

# 1-indexed inclusive ranges on the ORIGINAL service.py
COMMON_RANGES = [
    (25, 38),    # exceptions + _money_float
    (331, 355),  # _q, normalize/tokenize/match, _accounting_scope
]
CHART_RANGES = [
    (135, 328),  # templates + get_default_chart_of_accounts
    (543, 669),  # create/list/update/initialize accounts
]
COA_MAPPING_RANGES = [
    (358, 411),  # suggest_canonical_account
    (862, 1318), # source accounts + mappings CRUD/onboarding
]
REPORTS_RANGE = (1410, 2538)

# Quarantine stays in service.py
QUARANTINE_RANGES = [
    (41, 132),   # cash helpers + validate_cash_balance_for_journal_lines
    (414, 540),  # validate_journal_lines + idempotency signatures + validate_source
    (672, 859),  # post_journal_entry, reverse_journal_entry, _source_idempotency_key
    (1321, 1407),  # post_source_journal_entry
]

COMMON_HEADER = '''\
"""Shared accounting primitives (exceptions + scope/quantize helpers).

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

'''

CHART_HEADER = '''\
"""Chart of accounts templates and account CRUD.

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.common import AccountingNotFoundError, AccountingValidationError, _accounting_scope
from app.accounting.models import Account

'''

COA_HEADER = '''\
"""COA source-account mapping and onboarding helpers.

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.common import (
    AccountingNotFoundError,
    AccountingValidationError,
    _accounting_scope,
    _match_confidence,
    _normalize_key,
    _q,
    _tokenize,
)
from app.accounting.models import Account, CoaMapping, CoaSourceAccount
from app.accounting.schemas import CoaMappingIn, CoaSourceAccountIn

'''

REPORTS_HEADER = '''\
"""Accounting report and ledger read APIs.

Extracted from app/accounting/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
Posting core remains in app.accounting.service.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import Select, and_, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.accounting.common import (
    AccountingNotFoundError,
    AccountingValidationError,
    _accounting_scope,
    _money_float,
    _q,
)
from app.accounting.models import Account, JournalEntry, JournalLine

_logger = logging.getLogger(__name__)

'''

SERVICE_HEADER = '''\
"""Accounting service facade.

Quarantined posting core (LARGE_FILE_MODULARIZATION_PLAN.md §6):
validate_journal_lines, cash guards, post_journal_entry, reverse_journal_entry,
post_source_journal_entry. Chart/COA-mapping/report implementations live in
sibling modules and are re-exported here for compatibility.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.decorators import async_audit_logger

_logger = logging.getLogger(__name__)

from app.accounting.common import (
    AccountingIdempotencyConflictError as AccountingIdempotencyConflictError,
    AccountingNotFoundError as AccountingNotFoundError,
    AccountingValidationError as AccountingValidationError,
    _accounting_scope as _accounting_scope,
    _money_float as _money_float,
    _q as _q,
)
from app.accounting.models import Account, CoaMapping, CoaSourceAccount, JournalEntry, JournalLine
from app.accounting.schemas import (
    JournalLineIn,
    JournalPostRequest,
    SourceJournalLineIn,
    SourceJournalPostRequest,
)

'''


def read_lines() -> list[str]:
    return SERVICE.read_text(encoding="utf-8").splitlines(keepends=True)


def slice_lines(lines: list[str], start: int, end: int) -> str:
    return "".join(lines[start - 1 : end])


def join_ranges(lines: list[str], ranges: list[tuple[int, int]]) -> str:
    parts = []
    for start, end in ranges:
        parts.append(slice_lines(lines, start, end))
        parts.append("\n")
    return "".join(parts)


def build_facade_reexports() -> str:
    return '''
# Chart of accounts (moved to chart.py)
from app.accounting.chart import (  # noqa: E402
    DEFAULT_BUSINESS_CHART_OF_ACCOUNTS as DEFAULT_BUSINESS_CHART_OF_ACCOUNTS,
    DEFAULT_HOUSING_CHART_OF_ACCOUNTS as DEFAULT_HOUSING_CHART_OF_ACCOUNTS,
    create_account as create_account,
    get_default_chart_of_accounts as get_default_chart_of_accounts,
    initialize_default_chart_of_accounts as initialize_default_chart_of_accounts,
    list_accounts as list_accounts,
    update_account as update_account,
)

# COA mapping / onboarding (moved to coa_mapping.py)
from app.accounting.coa_mapping import (  # noqa: E402
    approve_coa_mappings as approve_coa_mappings,
    get_coa_mapping_gaps as get_coa_mapping_gaps,
    get_coa_onboarding_status as get_coa_onboarding_status,
    list_coa_mappings as list_coa_mappings,
    list_source_accounts as list_source_accounts,
    suggest_canonical_account as suggest_canonical_account,
    upsert_coa_mappings as upsert_coa_mappings,
    upsert_source_accounts as upsert_source_accounts,
)

# Reports / ledger reads (moved to reports/)
from app.accounting.reports import (  # noqa: E402
    _financial_year_start as _financial_year_start,
    _gl_sums_by_account as _gl_sums_by_account,
    _net_profit_from_rows as _net_profit_from_rows,
    get_accounts_payable as get_accounts_payable,
    get_accounts_receivable as get_accounts_receivable,
    get_balance_sheet as get_balance_sheet,
    get_business_dashboard as get_business_dashboard,
    get_cost_centre_account_actuals as get_cost_centre_account_actuals,
    get_cost_centre_ledger_pl as get_cost_centre_ledger_pl,
    get_journal_drilldown as get_journal_drilldown,
    get_journal_entry_detail as get_journal_entry_detail,
    get_journal_voucher_detail as get_journal_voucher_detail,
    get_ledger_lines as get_ledger_lines,
    get_party_ledger_lines as get_party_ledger_lines,
    get_party_outstanding as get_party_outstanding,
    get_party_wise_balances as get_party_wise_balances,
    get_profit_loss as get_profit_loss,
    get_receipts_payments as get_receipts_payments,
    get_trial_balance as get_trial_balance,
    list_journal_entries as list_journal_entries,
)
'''


def main() -> None:
    lines = read_lines()
    original = len(lines)
    if original < 2000:
        raise SystemExit(f"Expected ~2538 lines, got {original}. Already extracted?")

    COMMON.write_text(COMMON_HEADER + join_ranges(lines, COMMON_RANGES), encoding="utf-8", newline="\n")
    CHART.write_text(CHART_HEADER + join_ranges(lines, CHART_RANGES), encoding="utf-8", newline="\n")
    COA_MAPPING.write_text(COA_HEADER + join_ranges(lines, COA_MAPPING_RANGES), encoding="utf-8", newline="\n")
    REPORTS.write_text(
        REPORTS_HEADER + slice_lines(lines, REPORTS_RANGE[0], REPORTS_RANGE[1]) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    quarantine = join_ranges(lines, QUARANTINE_RANGES)
    # post_source_journal_entry needs list_accounts? No - uses mappings.
    # It calls post_journal_entry locally - fine.
    # It may call validate_source_journal_lines - stays in same file - fine.
    # chart create_account etc. imported later via re-export - post_source doesn't need them.

    # Quarantine block uses get_default? No.
    # initialize is in chart - posting uses validate_journal_lines locally.

    # Fix: post_source may reference suggest? No.
    # Cash helpers use _accounting_scope via common re-export - good.

    body = (
        SERVICE_HEADER
        + "\n# ════════════════════════════════════════════════════════════════════════\n"
        + "# QUARANTINED posting core (LARGE_FILE_MODULARIZATION_PLAN.md §6)\n"
        + "# ════════════════════════════════════════════════════════════════════════\n\n"
        + quarantine
        + build_facade_reexports()
    )
    SERVICE.write_text(body, encoding="utf-8", newline="\n")

    print(f"service.py: {original} -> {len(SERVICE.read_text(encoding='utf-8').splitlines())}")
    print(f"common.py: {len(COMMON.read_text(encoding='utf-8').splitlines())}")
    print(f"chart.py: {len(CHART.read_text(encoding='utf-8').splitlines())}")
    print(f"coa_mapping.py: {len(COA_MAPPING.read_text(encoding='utf-8').splitlines())}")
    print(f"reports.py: {len(REPORTS.read_text(encoding='utf-8').splitlines())}")


if __name__ == "__main__":
    main()
