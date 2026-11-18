"""MongoDB <-> PostgreSQL ledger reconciliation (Audit V1, SEC-07).

Business records (donations, seva bookings, maintenance collections, invoices, bills,
vouchers) live in MongoDB; their journal entries live in PostgreSQL. The two writes
are not one transaction, so a crash between them can leave a record without its
journal, or a journal without its record.

Every journal entry is posted with a deterministic idempotency key derived from its
source record (``don_<id>``, ``sales-invoice:<id>``...). This check matches the two
sides through that key, in both directions:

* ``missing_journal``    a record that should have posted has no journal entry.
* ``orphan_journal``     a journal entry whose source record no longer exists.
* ``unmarked_posting``   the journal exists but the record was never marked posted.

It only reports. It never posts, reverses or deletes anything: a person decides.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from bson import ObjectId
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models import JournalEntry
from app.db.mongo import get_collection

logger = logging.getLogger(__name__)

REPORTS_COLLECTION = "core_ledger_reconciliation_reports"
SAMPLE_LIMIT = 50
_KEY_BATCH = 500


def _amount(doc: dict[str, Any]) -> Decimal:
    try:
        return Decimal(str(doc.get("amount") or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


@dataclass(frozen=True)
class LedgerSource:
    name: str
    collection: str
    id_field: str
    key_prefix: str
    # Does this record have to have a journal entry?
    expects_journal: Callable[[dict[str, Any]], bool]
    # Idempotency key the record was (or will be) posted with.
    key_for: Callable[[dict[str, Any]], str | None]
    # Is the record marked as posted? (None: no such marker for this source.)
    is_marked_posted: Callable[[dict[str, Any]], bool] | None = None


def _simple_key(prefix: str, id_field: str) -> Callable[[dict[str, Any]], str | None]:
    def key(doc: dict[str, Any]) -> str | None:
        value = str(doc.get(id_field) or "").strip()
        return f"{prefix}{value}" if value else None

    return key


def _maintenance_key(doc: dict[str, Any]) -> str | None:
    collection_id = str(doc.get("collection_id") or "").strip()
    if not collection_id:
        return None
    bill_id, reference = doc.get("bill_id"), doc.get("reference")
    if bill_id and reference:
        return f"maintenance-bill:{doc.get('tenant_id')}:{doc.get('app_key')}:{bill_id}:{reference}"
    return f"maintenance:{collection_id}"


_POSTED_STATUSES = {"posted", "paid", "partially_paid", "reversed", "cancelled"}


def _business_posted(doc: dict[str, Any]) -> bool:
    return bool(doc.get("journal_entry_id")) or str(doc.get("status") or "") in _POSTED_STATUSES


SOURCES: tuple[LedgerSource, ...] = (
    LedgerSource(
        "mandir_donation", "mandir_donations", "donation_id", "don_",
        expects_journal=lambda d: _amount(d) > 0 and str(d.get("donation_type") or "") != "in_kind",
        key_for=_simple_key("don_", "donation_id"),
    ),
    LedgerSource(
        "mandir_seva_booking", "mandir_seva_bookings", "id", "sev_",
        expects_journal=lambda d: _amount(d) > 0,
        key_for=_simple_key("sev_", "id"),
    ),
    LedgerSource(
        "temple_donation", "temple_donations", "donation_id", "donation:",
        expects_journal=lambda d: True,
        key_for=_simple_key("donation:", "donation_id"),
    ),
    LedgerSource(
        "temple_seva_collection", "temple_seva_collections", "seva_collection_id", "seva:",
        expects_journal=lambda d: True,
        key_for=_simple_key("seva:", "seva_collection_id"),
    ),
    LedgerSource(
        "housing_maintenance_collection", "housing_maintenance_collections", "collection_id", "maintenance:",
        expects_journal=lambda d: True,
        key_for=_maintenance_key,
    ),
    LedgerSource(
        "business_sales_invoice", "business_sales_invoices", "invoice_id", "sales-invoice:",
        expects_journal=_business_posted,
        key_for=_simple_key("sales-invoice:", "invoice_id"),
        is_marked_posted=_business_posted,
    ),
    LedgerSource(
        "business_purchase_bill", "business_purchase_bills", "bill_id", "purchase-bill:",
        expects_journal=_business_posted,
        key_for=_simple_key("purchase-bill:", "bill_id"),
        is_marked_posted=_business_posted,
    ),
    LedgerSource(
        "business_voucher", "business_vouchers", "voucher_id", "business-voucher:",
        expects_journal=_business_posted,
        key_for=_simple_key("business-voucher:", "voucher_id"),
        is_marked_posted=_business_posted,
    ),
)


@dataclass
class SourceResult:
    checked_records: int = 0
    checked_journals: int = 0
    missing_journal: list[dict[str, Any]] = field(default_factory=list)
    orphan_journal: list[dict[str, Any]] = field(default_factory=list)
    unmarked_posting: list[dict[str, Any]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "checked_records": self.checked_records,
            "checked_journals": self.checked_journals,
            "missing_journal": len(self.missing_journal),
            "orphan_journal": len(self.orphan_journal),
            "unmarked_posting": len(self.unmarked_posting),
        }


def _scope(doc: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(doc.get("tenant_id") or ""),
        str(doc.get("app_key") or ""),
        str(doc.get("accounting_entity_id") or "primary"),
    )


async def _existing_keys(
    session: AsyncSession, scope: tuple[str, str, str], keys: list[str]
) -> set[str]:
    tenant_id, app_key, entity = scope
    found: set[str] = set()
    for start in range(0, len(keys), _KEY_BATCH):
        batch = keys[start : start + _KEY_BATCH]
        rows = await session.execute(
            select(JournalEntry.idempotency_key).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.app_key == app_key,
                JournalEntry.accounting_entity_id == entity,
                JournalEntry.idempotency_key.in_(batch),
            )
        )
        found.update(str(k) for k in rows.scalars().all() if k)
    return found


def _record_id_from_key(source: LedgerSource, key: str) -> str | None:
    if source.name == "housing_maintenance_collection":
        return key[len(source.key_prefix):] if key.startswith(source.key_prefix) else None
    return key[len(source.key_prefix):] or None


async def reconcile_ledger(
    session: AsyncSession,
    *,
    since: datetime,
    until: datetime | None = None,
    tenant_id: str | None = None,
    grace: timedelta = timedelta(minutes=15),
    limit_per_source: int = 20000,
) -> dict[str, Any]:
    """Compare records and journal entries created between ``since`` and ``until``.

    Items newer than ``grace`` are skipped so in-flight requests are not reported.
    """
    now = datetime.now(timezone.utc)
    until = min(until or now, now - grace)
    results: dict[str, SourceResult] = {}

    for source in SOURCES:
        result = SourceResult()
        results[source.name] = result
        try:
            collection = get_collection(source.collection)
        except RuntimeError:
            continue

        # 1. Records -> journal entries.
        query: dict[str, Any] = {
            "_id": {"$gte": ObjectId.from_datetime(since), "$lte": ObjectId.from_datetime(until)}
        }
        if tenant_id:
            query["tenant_id"] = tenant_id
        docs = await collection.find(query).limit(limit_per_source).to_list(length=limit_per_source)
        result.checked_records = len(docs)
        expected: dict[tuple[str, str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
        for doc in docs:
            key = source.key_for(doc)
            if key and source.expects_journal(doc):
                expected[_scope(doc)][key] = doc
        for scope, by_key in expected.items():
            present = await _existing_keys(session, scope, list(by_key))
            for key, doc in by_key.items():
                if key not in present:
                    result.missing_journal.append(_record_sample(source, doc, key))

        # 2. Journal entries -> records.
        journal_query = select(
            JournalEntry.id,
            JournalEntry.tenant_id,
            JournalEntry.app_key,
            JournalEntry.idempotency_key,
            JournalEntry.created_at,
        ).where(
            JournalEntry.created_at >= since,
            JournalEntry.created_at <= until,
            # startswith(autoescape): "_" in "don_" must not act as a SQL wildcard.
            or_(*[JournalEntry.idempotency_key.startswith(p, autoescape=True) for p in _prefixes(source)]),
        )
        if tenant_id:
            journal_query = journal_query.where(JournalEntry.tenant_id == tenant_id)
        rows = (await session.execute(journal_query.limit(limit_per_source))).all()
        result.checked_journals = len(rows)
        for row in rows:
            record = await _find_record(collection, source, row)
            if record is None:
                result.orphan_journal.append(_journal_sample(row))
            elif source.is_marked_posted and not source.is_marked_posted(record):
                result.unmarked_posting.append(_journal_sample(row))

    issues = sum(
        len(r.missing_journal) + len(r.orphan_journal) + len(r.unmarked_posting) for r in results.values()
    )
    return {
        "generated_at": now.isoformat(),
        "window": {"since": since.isoformat(), "until": until.isoformat()},
        "tenant_id": tenant_id,
        "issue_count": issues,
        "sources": {
            name: {
                **r.counts(),
                "samples": {
                    "missing_journal": r.missing_journal[:SAMPLE_LIMIT],
                    "orphan_journal": r.orphan_journal[:SAMPLE_LIMIT],
                    "unmarked_posting": r.unmarked_posting[:SAMPLE_LIMIT],
                },
            }
            for name, r in results.items()
        },
    }


def _prefixes(source: LedgerSource) -> list[str]:
    if source.name == "housing_maintenance_collection":
        return ["maintenance:", "maintenance-bill:"]
    return [source.key_prefix]


async def _find_record(collection, source: LedgerSource, row) -> dict[str, Any] | None:
    key = str(row.idempotency_key or "")
    base = {"tenant_id": row.tenant_id, "app_key": row.app_key}
    if source.name == "housing_maintenance_collection" and key.startswith("maintenance-bill:"):
        parts = key.split(":", 4)
        if len(parts) == 5:
            return await collection.find_one({**base, "bill_id": parts[3], "reference": parts[4]})
        return None
    record_id = _record_id_from_key(source, key)
    if not record_id:
        return None
    return await collection.find_one({**base, source.id_field: record_id})


def _record_sample(source: LedgerSource, doc: dict[str, Any], key: str) -> dict[str, Any]:
    return {
        "record_id": str(doc.get(source.id_field) or ""),
        "tenant_id": doc.get("tenant_id"),
        "app_key": doc.get("app_key"),
        "amount": str(doc.get("amount") or doc.get("total_amount") or doc.get("grand_total") or ""),
        "expected_idempotency_key": key,
    }


def _journal_sample(row) -> dict[str, Any]:
    return {
        "journal_entry_id": row.id,
        "tenant_id": row.tenant_id,
        "app_key": row.app_key,
        "idempotency_key": row.idempotency_key,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def save_report(report: dict[str, Any]) -> None:
    await get_collection(REPORTS_COLLECTION).insert_one(dict(report))


# ----------------------------------------------------------------- background run

_WORKER_TASK: asyncio.Task | None = None
_STOP_EVENT: asyncio.Event | None = None


async def _run_once(lookback: timedelta) -> dict[str, Any] | None:
    from app.db.postgres import get_session_factory

    try:
        factory = get_session_factory()
    except RuntimeError:
        return None
    async with factory() as session:
        report = await reconcile_ledger(session, since=datetime.now(timezone.utc) - lookback)
    with suppress(Exception):
        await save_report(report)
    if report["issue_count"]:
        logger.warning(
            "Ledger reconciliation found %d issue(s); see %s or GET /api/v1/platform-owner/ledger-reconciliation",
            report["issue_count"],
            REPORTS_COLLECTION,
        )
    else:
        logger.info("Ledger reconciliation clean for the last %s", lookback)
    return report


async def _loop(stop: asyncio.Event, interval: timedelta, lookback: timedelta) -> None:
    # Let the app finish starting before the first pass.
    with suppress(asyncio.TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=600)
    while not stop.is_set():
        try:
            await _run_once(lookback)
        except Exception:
            logger.exception("Ledger reconciliation run failed")
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval.total_seconds())


async def start_ledger_reconciliation_worker(*, interval_hours: float, lookback_days: float) -> bool:
    global _WORKER_TASK, _STOP_EVENT
    if interval_hours <= 0:
        return False
    if _WORKER_TASK and not _WORKER_TASK.done():
        return True
    _STOP_EVENT = asyncio.Event()
    _WORKER_TASK = asyncio.create_task(
        _loop(_STOP_EVENT, timedelta(hours=interval_hours), timedelta(days=lookback_days)),
        name="ledger-reconciliation-worker",
    )
    logger.info("Ledger reconciliation worker started (every %sh, looking back %s days)", interval_hours, lookback_days)
    return True


async def stop_ledger_reconciliation_worker() -> None:
    global _WORKER_TASK
    if _STOP_EVENT is not None:
        _STOP_EVENT.set()
    if _WORKER_TASK is not None:
        with suppress(Exception):
            await asyncio.wait_for(_WORKER_TASK, timeout=5)
    _WORKER_TASK = None
