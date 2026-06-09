"""Backfill journal_lines.party_id for ledger rows posted before the party
sub-ledger existed, so historical Sundry Debtors / Creditors balances attribute
to the right customer/vendor (instead of the "Unallocated" bucket).

Maps each receivable/payable journal line to a party via its source document in
MongoDB:
  - sales_invoice -> business_sales_invoices.customer_party_id
  - purchase_bill -> business_purchase_bills.vendor_party_id
  - credit_note   -> business_credit_notes.customer_party_id
  - debit_note    -> business_debit_notes.vendor_party_id
  - typed vouchers (no source_document_type) -> business_vouchers, matched by
    reference/voucher_number, party on the receivable line (receipt) or payable
    line (payment)
  - journal_reversal -> resolves the ORIGINAL entry's source document

Posted ledger rows are immutable (a trigger blocks UPDATE), so updates run with
`session_replication_role = replica` to bypass the trigger. This requires a
table-owner / superuser role (true for the local and Render Postgres users).

Usage:
  python scripts/backfill_journal_party.py --app-key mitrabooks [--tenant-id T]
  python scripts/backfill_journal_party.py --app-key mitrabooks --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import text

from app.db.mongo import close_mongo, get_collection, init_mongo
from app.db.postgres import close_postgres, get_session_factory, init_postgres

# source_document_type -> (mongo collection, id field, party field)
SOURCE_PARTY = {
    "sales_invoice": ("business_sales_invoices", "invoice_id", "customer_party_id"),
    "purchase_bill": ("business_purchase_bills", "bill_id", "vendor_party_id"),
    "credit_note": ("business_credit_notes", "credit_note_id", "customer_party_id"),
    "debit_note": ("business_debit_notes", "debit_note_id", "vendor_party_id"),
}


async def _party_for_source(cache: dict, source_type: str, source_id: str) -> str | None:
    if not source_type or not source_id:
        return None
    spec = SOURCE_PARTY.get(source_type)
    if spec is None:
        return None
    collection, id_field, party_field = spec
    key = (collection, source_id)
    if key not in cache:
        doc = await get_collection(collection).find_one({id_field: source_id})
        cache[key] = (doc or {}).get(party_field)
    return cache[key]


async def _party_for_voucher(cache: dict, *, tenant_id, app_key, reference, is_receivable) -> str | None:
    """Vouchers carry no source linkage; match by reference/voucher_number.
    Tag only the side matching the line: receipt -> receivable, payment -> payable."""
    if not reference:
        return None
    key = ("voucher", tenant_id, app_key, reference)
    if key not in cache:
        doc = await get_collection("business_vouchers").find_one({
            "tenant_id": tenant_id, "app_key": app_key, "voucher_number": reference,
        })
        cache[key] = doc
    doc = cache[key]
    if not doc or not doc.get("party_id"):
        return None
    vtype = doc.get("voucher_type")
    if (is_receivable and vtype == "receipt") or ((not is_receivable) and vtype == "payment"):
        return doc.get("party_id")
    return None


_TRIGGER = "trg_journal_lines_no_update_delete"


async def _do_updates(session, updates: list[tuple[int, str]]) -> None:
    for line_id, party in updates:
        await session.execute(
            text("UPDATE journal_lines SET party_id = :pid WHERE id = :lid AND party_id IS NULL"),
            {"pid": party, "lid": line_id},
        )


async def _apply_updates(sf, updates: list[tuple[int, str]]) -> None:
    """Write party_id past the posted-ledger immutability trigger.

    Prefers `session_replication_role = replica` (needs superuser; true for a
    local dev DB). Falls back to `ALTER TABLE ... DISABLE/ENABLE TRIGGER`, which
    only needs table ownership (true for the managed Render Postgres role) and is
    more surgical — it suspends only the immutability trigger, not all triggers.
    """
    # Path A: replication-role bypass (superuser only). If the SET is rejected
    # the transaction aborts cleanly here (no UPDATE attempted), so we can detect
    # the privilege error and fall back without masking it.
    try:
        async with sf() as session:
            await session.execute(text("SET session_replication_role = replica"))
            await _do_updates(session, updates)
            await session.execute(text("SET session_replication_role = DEFAULT"))
            await session.commit()
        return
    except Exception as exc:  # InsufficientPrivilege on non-superuser roles
        if "session_replication_role" not in str(exc):
            raise
        print("session_replication_role unavailable (non-superuser); "
              "falling back to DISABLE TRIGGER (table-owner privilege).")

    # Path B: disable just the immutability trigger (table owner).
    async with sf() as session:
        await session.execute(text(f"ALTER TABLE journal_lines DISABLE TRIGGER {_TRIGGER}"))
        try:
            await _do_updates(session, updates)
            await session.commit()
        finally:
            await session.execute(text(f"ALTER TABLE journal_lines ENABLE TRIGGER {_TRIGGER}"))
            await session.commit()


async def run(args: argparse.Namespace) -> None:
    await init_mongo()
    await init_postgres()
    sf = get_session_factory()

    scope = "WHERE je.app_key = :app_key"
    params = {"app_key": args.app_key}
    if args.tenant_id:
        scope += " AND je.tenant_id = :tenant_id"
        params["tenant_id"] = args.tenant_id
    if args.entity:
        scope += " AND je.accounting_entity_id = :entity"
        params["entity"] = args.entity

    # Candidate lines: on a receivable/payable account, not yet tagged.
    select_sql = text(f"""
        SELECT jl.id AS line_id, jl.tenant_id, jl.app_key,
               a.is_receivable, a.is_payable,
               je.source_document_type, je.source_document_id, je.reference
        FROM journal_lines jl
        JOIN journal_entries je ON je.id = jl.journal_id
        JOIN accounts a ON a.id = jl.account_id
        {scope}
          AND (a.is_receivable OR a.is_payable)
          AND jl.party_id IS NULL
    """)

    async with sf() as session:
        rows = (await session.execute(select_sql, params)).mappings().all()

    print(f"Found {len(rows)} untagged receivable/payable lines in scope.")

    cache: dict = {}
    updates: list[tuple[int, str]] = []
    skipped = 0
    for r in rows:
        stype = r["source_document_type"]
        sid = r["source_document_id"]
        party = None

        if stype == "journal_reversal" and sid:
            # Resolve the original entry's source, then map that.
            async with sf() as s2:
                orig = (await s2.execute(text(
                    "SELECT source_document_type, source_document_id, reference FROM journal_entries WHERE id = :id"
                ), {"id": int(sid)})).mappings().first()
            if orig:
                party = await _party_for_source(cache, orig["source_document_type"], orig["source_document_id"])
                if party is None:
                    party = await _party_for_voucher(
                        cache, tenant_id=r["tenant_id"], app_key=r["app_key"],
                        reference=orig["reference"], is_receivable=r["is_receivable"],
                    )
        elif stype in SOURCE_PARTY:
            party = await _party_for_source(cache, stype, sid)
        else:
            party = await _party_for_voucher(
                cache, tenant_id=r["tenant_id"], app_key=r["app_key"],
                reference=r["reference"], is_receivable=r["is_receivable"],
            )

        if party:
            updates.append((r["line_id"], party))
        else:
            skipped += 1

    print(f"Resolved {len(updates)} lines to a party; {skipped} left unattributed (no source / manual entries).")

    if args.dry_run:
        for line_id, party in updates[:20]:
            print(f"  [dry-run] line {line_id} -> {party}")
        if len(updates) > 20:
            print(f"  ... and {len(updates) - 20} more")
        print("Dry run: no changes written.")
    elif updates:
        await _apply_updates(sf, updates)
        print(f"Backfilled party_id on {len(updates)} journal lines.")

    await close_postgres()
    await close_mongo()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill journal_lines.party_id from business source documents.")
    parser.add_argument("--app-key", default="mitrabooks")
    parser.add_argument("--tenant-id", default=None, help="Limit to one tenant (default: all tenants for the app).")
    parser.add_argument("--entity", default=None, help="Limit to one accounting entity (e.g. 'primary').")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing.")
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
