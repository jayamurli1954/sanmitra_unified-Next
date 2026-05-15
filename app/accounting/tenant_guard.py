from app.accounting.context import resolve_accounting_context


def enforce_accounting_tenant_isolation(*, tenant_id: str, app_key: str | None) -> None:
    resolve_accounting_context(
        current_user={"tenant_id": tenant_id, "app_key": app_key, "sub": "system"},
        x_tenant_id=tenant_id,
        x_app_key=app_key,
    )
