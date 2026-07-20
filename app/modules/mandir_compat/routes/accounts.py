"""MandirMitra chart-of-accounts list, edit, and import routes.

Extracted verbatim from app/modules/mandir_compat/router.py per
docs/operations/LARGE_FILE_MODULARIZATION_PLAN.md. Pure move: logic unchanged.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.models.entities import Account
from app.core.auth.dependencies import get_current_user
from app.db.postgres import get_async_session
from app.modules.mandir_compat import router as mandir_router
from app.modules.mandir_compat.router import _MANDIR_ADMIN_ROUTE_DEPS, router


def _ok(name: str, **extra: Any) -> dict[str, Any]:
    return {"status": "ok", "endpoint": name, **extra}


@router.get("/accounts")
async def mandir_accounts_list(_current_user: dict = Depends(get_current_user)):
    tenant_id = mandir_router.resolve_tenant_id(_current_user, None)
    app_key = mandir_router.resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._ensure_default_mandir_accounts(tenant_id, app_key)
    accounts = mandir_router.get_collection("accounting_accounts")
    docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=500)
    unique_docs = mandir_router._dedupe_mandir_account_docs(docs)
    return [mandir_router._mandir_account_view(doc) for doc in unique_docs]


@router.get("/accounts/hierarchy")
async def mandir_accounts_hierarchy(_current_user: dict = Depends(get_current_user)):
    tenant_id = mandir_router.resolve_tenant_id(_current_user, None)
    app_key = mandir_router.resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())
    await mandir_router._ensure_default_mandir_accounts(tenant_id, app_key)
    accounts = mandir_router.get_collection("accounting_accounts")
    docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key, "is_active": True}).to_list(length=500)
    unique_docs = mandir_router._dedupe_mandir_account_docs(docs)
    return [mandir_router._mandir_account_view(doc) for doc in unique_docs]


@router.put("/accounts/{account_id}", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_accounts_update(
    account_id: str,
    payload: dict[str, Any],
    reason: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    tenant_id = mandir_router.resolve_tenant_id(_current_user, x_tenant_id)
    app_key = mandir_router.resolve_app_key((x_app_key or _current_user.get("app_key") or "mandirmitra").strip())

    reason_text = str(reason or "").strip()
    if not reason_text:
        raise HTTPException(status_code=400, detail="Reason is required for audit trail")

    accounts = mandir_router.get_collection("accounting_accounts")
    docs = await accounts.find({"tenant_id": tenant_id, "app_key": app_key}).to_list(length=1000)

    raw_identifier = str(account_id or "").strip()
    normalized_identifier = mandir_router._normalize_mandir_account_code(raw_identifier)

    def _matches_identifier(doc: dict[str, Any]) -> bool:
        doc_id = str(doc.get("account_id") or "").strip()
        doc_code = str(doc.get("account_code") or doc.get("account_id") or "").strip()
        normalized_doc_code = mandir_router._normalize_mandir_account_code(
            doc_code,
            account_name=doc.get("account_name") or doc.get("name"),
        )
        return raw_identifier in {doc_id, doc_code, normalized_doc_code} or normalized_identifier in {doc_id, doc_code, normalized_doc_code}

    target_doc = next((doc for doc in docs if _matches_identifier(doc)), None)
    if target_doc is None:
        raise HTTPException(status_code=404, detail="Account not found")

    updated_name = str(payload.get("account_name") or target_doc.get("account_name") or target_doc.get("name") or "").strip()
    if not updated_name:
        raise HTTPException(status_code=400, detail="Account name is required")

    now = datetime.now(timezone.utc).isoformat()
    account_code = mandir_router._normalize_mandir_account_code(
        target_doc.get("account_code") or target_doc.get("account_id") or raw_identifier,
        account_name=target_doc.get("account_name") or target_doc.get("name"),
    )

    update_doc: dict[str, Any] = {
        "account_name": updated_name,
        "name": updated_name,
        "updated_at": now,
        "updated_by": str(_current_user.get("sub") or _current_user.get("email") or "system"),
        "update_reason": reason_text,
    }

    if "account_name_kannada" in payload:
        update_doc["account_name_kannada"] = mandir_router._safe_optional_str(payload.get("account_name_kannada"))
    if "description" in payload:
        update_doc["description"] = mandir_router._safe_optional_str(payload.get("description"))

    update_query = {"tenant_id": tenant_id, "app_key": app_key}
    if account_code:
        update_query["account_code"] = account_code
    else:
        update_query["account_id"] = target_doc.get("account_id")

    await accounts.update_one(update_query, {"$set": update_doc}, upsert=False)

    if account_code:
        try:
            account_stmt = select(Account).where(
                Account.tenant_id == tenant_id,
                Account.code == account_code,
            )
            sql_account = (await session.execute(account_stmt)).scalar_one_or_none()
            if sql_account is not None and str(sql_account.name or "").strip() != updated_name:
                sql_account.name = updated_name
                await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            mandir_router.logger.warning(
                "Failed to sync SQL account name for tenant %s code %s: %s",
                tenant_id,
                account_code,
                exc,
            )

    try:
        old_value = {
            "account_name": target_doc.get("account_name") or target_doc.get("name"),
            "account_name_kannada": target_doc.get("account_name_kannada"),
            "description": target_doc.get("description"),
        }
        new_value = {
            "account_name": update_doc.get("account_name"),
            "account_name_kannada": update_doc.get("account_name_kannada", old_value.get("account_name_kannada")),
            "description": update_doc.get("description", old_value.get("description")),
            "reason": reason_text,
        }
        await mandir_router.log_audit_event(
            tenant_id=tenant_id,
            user_id=str(_current_user.get("sub") or _current_user.get("email") or "system"),
            product="mandirmitra",
            action="coa_account_updated",
            entity_type="accounting_account",
            entity_id=str(account_code or target_doc.get("account_id") or raw_identifier),
            old_value=old_value,
            new_value=new_value,
        )
    except Exception as exc:
        mandir_router.logger.warning("Failed to write COA update audit log for tenant %s: %s", tenant_id, exc)

    updated_doc = await accounts.find_one(update_query)
    if not updated_doc:
        updated_doc = {**target_doc, **update_doc, "account_code": account_code}

    return mandir_router._mandir_account_view(updated_doc)

@router.post("/accounts/import-legacy", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_accounts_import_legacy(
    payload: dict[str, Any] | None = None,
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
):
    tenant_id = mandir_router.resolve_tenant_id(_current_user, None)
    app_key = mandir_router.resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())

    seed_rows = payload.get("items") if isinstance(payload, dict) else None
    if seed_rows is None:
        seed_rows = mandir_router._load_mandir_legacy_accounts()

    if not isinstance(seed_rows, list) or not seed_rows:
        raise HTTPException(status_code=400, detail="Legacy COA payload is empty")

    normalized_seed_rows = [row for row in seed_rows if isinstance(row, dict)]
    mongo_result = await mandir_router._upsert_mandir_account_docs(tenant_id, app_key, normalized_seed_rows)
    sql_result = await mandir_router._sync_mandir_sql_accounts_from_seed(
        session,
        tenant_id=tenant_id,
        seed_rows=normalized_seed_rows,
    )
    await mandir_router._normalize_mandir_income_accounts(session, tenant_id)
    return _ok(
        "accounts/import-legacy",
        message="Legacy accounts imported",
        created=mongo_result["created"],
        reactivated=mongo_result["reactivated"],
        updated=mongo_result["updated"],
        total=mongo_result["total"],
        sql_created=sql_result["created"],
        sql_updated=sql_result["updated"],
        sql_total=sql_result["total"],
    )


@router.post("/accounts/initialize-default", dependencies=_MANDIR_ADMIN_ROUTE_DEPS)
async def mandir_accounts_initialize_default(
    session: AsyncSession = Depends(get_async_session),
    _current_user: dict = Depends(get_current_user),
):
    tenant_id = mandir_router.resolve_tenant_id(_current_user, None)
    app_key = mandir_router.resolve_app_key((_current_user.get("app_key") or "mandirmitra").strip())
    seed_rows = mandir_router._mandir_seed_accounts()
    mongo_result = await mandir_router._upsert_mandir_account_docs(tenant_id, app_key, seed_rows)
    sql_result = await mandir_router._sync_mandir_sql_accounts_from_seed(
        session,
        tenant_id=tenant_id,
        seed_rows=seed_rows,
    )
    await mandir_router._normalize_mandir_income_accounts(session, tenant_id)
    return _ok(
        "accounts/initialize-default",
        message="Default accounts initialized",
        created=mongo_result["created"],
        reactivated=mongo_result["reactivated"],
        updated=mongo_result["updated"],
        sql_created=sql_result["created"],
        sql_updated=sql_result["updated"],
        sql_total=sql_result["total"],
    )

