"""Mongo index bootstrap for MitraBooks business collections.

Extracted verbatim from app/modules/business/service.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class _TolerantIndexCollection:
    """Wraps a collection so one failing `create_index` (for example a unique
    index that cannot be built because existing production data already has
    duplicates) is logged and recorded instead of aborting every index after it."""

    def __init__(self, collection, name: str, failures: list[dict]):
        self._collection = collection
        self._name = name
        self._failures = failures

    async def create_index(self, keys, **kwargs):
        try:
            return await self._collection.create_index(keys, **kwargs)
        except Exception as exc:  # noqa: BLE001 - every failure is logged and reported
            # Never log or keep the exception text: for a unique index blocked by
            # duplicates, MongoDB's message contains the duplicated values
            # themselves (party codes, GSTINs, names...). Record only what is
            # needed to find the index: collection, field names, error type/code.
            error_type = type(exc).__name__
            error_code = getattr(exc, "code", None)
            self._failures.append({
                "collection": self._name,
                "fields": [str(field) for field, _direction in keys],
                "unique": bool(kwargs.get("unique")),
                "error_type": error_type,
                "error_code": error_code,
            })
            # Log only the failure count position, error type and code: no
            # exception text, field names or other values derived from data.
            logger.error(
                "Could not create MitraBooks business index #%d (%s, code %s); "
                "a unique index usually fails because existing documents contain duplicates. "
                "ensure_business_indexes() returns the collection and fields.",
                len(self._failures),
                error_type,
                error_code,
            )
            return None


async def ensure_business_indexes() -> list[dict]:
    """Create the MitraBooks business indexes (idempotent).

    Runs at application startup and from the E2E seed. Each index is created
    independently; failures are logged and returned rather than raised, so
    one index that cannot be built does not leave the rest missing."""
    # Imported here, not at module level: business.service imports this module
    # at load time, so a module-level import back would be a cyclic import.
    from app.modules.business import service as business_service

    failures: list[dict] = []

    def get_collection(name: str):
        return _TolerantIndexCollection(business_service.get_collection(name), name, failures)

    parties = get_collection(business_service.PARTIES_COLLECTION)
    await parties.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("party_code", 1)], unique=True)
    await parties.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("party_type", 1)])
    vouchers = get_collection(business_service.VOUCHERS_COLLECTION)
    await vouchers.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("entry_date", -1)])
    await vouchers.create_index([("tenant_id", 1), ("app_key", 1), ("voucher_id", 1)], unique=True)
    await vouchers.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    ca_documents = get_collection(business_service.CA_DOCUMENTS_COLLECTION)
    await ca_documents.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("updated_at", -1)])
    await ca_documents.create_index([("tenant_id", 1), ("app_key", 1), ("document_id", 1)], unique=True)
    ca_clients = get_collection(business_service.CA_CLIENTS_COLLECTION)
    await ca_clients.create_index([("tenant_id", 1), ("app_key", 1), ("client_id", 1)], unique=True)
    await ca_clients.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("client_name", 1)])
    attachments = get_collection(business_service.BUSINESS_DOCUMENT_ATTACHMENTS_COLLECTION)
    await attachments.create_index([("tenant_id", 1), ("app_key", 1), ("attachment_id", 1)], unique=True)
    await attachments.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("owner_type", 1), ("owner_id", 1), ("uploaded_at", -1)])
    invoices = get_collection(business_service.SALES_INVOICES_COLLECTION)
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("invoice_date", -1)])
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("invoice_id", 1)], unique=True)
    await invoices.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    invoice_settings = get_collection(business_service.INVOICE_SETTINGS_COLLECTION)
    await invoice_settings.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1)], unique=True)
    admin_settings = get_collection(business_service.ADMIN_SETTINGS_COLLECTION)
    await admin_settings.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1)], unique=True)
    bills = get_collection(business_service.PURCHASE_BILLS_COLLECTION)
    await bills.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("bill_date", -1)])
    await bills.create_index([("tenant_id", 1), ("app_key", 1), ("bill_id", 1)], unique=True)
    await bills.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    period_locks = get_collection(business_service.GST_PERIOD_LOCKS_COLLECTION)
    await period_locks.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("period", 1)], unique=True)
    credit_notes = get_collection(business_service.CREDIT_NOTES_COLLECTION)
    await credit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("note_date", -1)])
    await credit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("credit_note_id", 1)], unique=True)
    await credit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    debit_notes = get_collection(business_service.DEBIT_NOTES_COLLECTION)
    await debit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("note_date", -1)])
    await debit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("debit_note_id", 1)], unique=True)
    await debit_notes.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    gst_settlements = get_collection(business_service.GST_SETTLEMENTS_COLLECTION)
    await gst_settlements.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("period", 1)], unique=True)
    payment_allocations = get_collection("business_payment_allocations")
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("allocation_id", 1)], unique=True)
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("side", 1), ("status", 1)])
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("open_item_id", 1)])
    await payment_allocations.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("payment_id", 1)])
    bank_stmt_lines = get_collection("business_bank_statement_lines")
    await bank_stmt_lines.create_index([("tenant_id", 1), ("app_key", 1), ("statement_line_id", 1)], unique=True)
    await bank_stmt_lines.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("account_id", 1), ("txn_date", 1)])
    await bank_stmt_lines.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("account_id", 1), ("dedupe_key", 1)], unique=True)
    bank_matches = get_collection("business_bank_recon_matches")
    await bank_matches.create_index([("tenant_id", 1), ("app_key", 1), ("match_id", 1)], unique=True)
    await bank_matches.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("account_id", 1), ("status", 1)])
    # Line claims are unique by `_id` (always indexed); this index only speeds
    # up releasing a match's claims on unmatch.
    bank_claims = get_collection("business_bank_recon_line_claims")
    await bank_claims.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("owner_id", 1)])
    dunning_log = get_collection("business_dunning_log")
    await dunning_log.create_index([("tenant_id", 1), ("app_key", 1), ("dunning_id", 1)], unique=True)
    await dunning_log.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("party_id", 1), ("created_at", -1)])
    fixed_assets_col = get_collection("business_fixed_assets")
    await fixed_assets_col.create_index([("tenant_id", 1), ("app_key", 1), ("asset_id", 1)], unique=True)
    await fixed_assets_col.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("purchase_date", 1)])
    depreciation_runs = get_collection("business_depreciation_runs")
    await depreciation_runs.create_index([("tenant_id", 1), ("app_key", 1), ("run_id", 1)], unique=True)
    await depreciation_runs.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("financial_year", 1), ("status", 1)])
    dimensions_col = get_collection("business_dimensions")
    await dimensions_col.create_index([("tenant_id", 1), ("app_key", 1), ("dimension_id", 1)], unique=True)
    await dimensions_col.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("dimension_type", 1), ("code", 1)], unique=True)
    items_col = get_collection("business_items")
    await items_col.create_index([("tenant_id", 1), ("app_key", 1), ("item_id", 1)], unique=True)
    await items_col.create_index([("tenant_id", 1), ("app_key", 1), ("accounting_entity_id", 1), ("code", 1)], unique=True)
    if failures:
        logger.error(
            "MitraBooks business indexes: %d could not be created. The return value of "
            "ensure_business_indexes() names the collection and fields of each.",
            len(failures),
        )
    return failures
