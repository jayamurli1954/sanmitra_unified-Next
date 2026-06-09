"""One-shot diagnostic for the business dashboard returning zeros/failing.

Run on the server (Render Shell) where the real DB + env are available:

    python scripts/diag_dashboard.py

It auto-detects the mitrabooks business scope (no hard-coded tenant), runs the
exact dashboard computation the API uses, prints a Trial Balance comparison, and
dumps account types/flags — so we can see whether the dashboard raises, returns
zeros (scope/date/flag mismatch), or works (pointing at the HTTP layer).
"""
from __future__ import annotations

import asyncio
import sys
import traceback
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import func, select

from app.accounting.models import Account
from app.accounting.service import get_business_dashboard, get_trial_balance
from app.db.postgres import close_postgres, get_session_factory, init_postgres


async def main() -> None:
    await init_postgres()
    sf = get_session_factory()
    async with sf() as s:
        scopes = (await s.execute(
            select(Account.tenant_id, Account.app_key, Account.accounting_entity_id, func.count())
            .group_by(Account.tenant_id, Account.app_key, Account.accounting_entity_id)
        )).all()
        print("\n=== SCOPES (tenant, app_key, entity, #accounts) ===")
        for r in scopes:
            print("  ", tuple(r))

        # Pick the mitrabooks scope with the most accounts (the live business books).
        business = [r for r in scopes if r[1] == "mitrabooks"]
        if not business:
            print("\nNo accounts found for app_key='mitrabooks'. Stopping.")
            await close_postgres()
            return
        business.sort(key=lambda r: r[3], reverse=True)
        T, A, E = business[0][0], business[0][1], business[0][2]
        print(f"\n=== Using scope: tenant={T!r} app_key={A!r} entity={E!r} ===")

        as_of = date.today()
        print(f"as_of = {as_of.isoformat()}")

        try:
            dash = await get_business_dashboard(s, tenant_id=T, app_key=A, accounting_entity_id=E, as_of=as_of)
            print("\n=== DASHBOARD RESULT ===")
            for k, v in dash.items():
                print(f"  {k}: {v}")
        except Exception:
            print("\n=== DASHBOARD RAISED ===")
            traceback.print_exc()

        try:
            lines, td, tc = await get_trial_balance(s, tenant_id=T, as_of=as_of, app_key=A, accounting_entity_id=E)
            print(f"\n=== TRIAL BALANCE (same scope): rows={len(lines)} total_debit={td} total_credit={tc} ===")
        except Exception:
            print("\n=== TRIAL BALANCE RAISED ===")
            traceback.print_exc()

        rows = (await s.execute(
            select(Account.code, Account.name, Account.type,
                   Account.is_cash_bank, Account.is_receivable, Account.is_payable)
            .where(Account.tenant_id == T, Account.app_key == A, Account.accounting_entity_id == E)
            .order_by(Account.code)
        )).all()
        print(f"\n=== ACCOUNTS in scope: {len(rows)} (code, name, type, cash?, recv?, pay?) ===")
        for r in rows:
            print("  ", tuple(r))

    await close_postgres()


if __name__ == "__main__":
    asyncio.run(main())
