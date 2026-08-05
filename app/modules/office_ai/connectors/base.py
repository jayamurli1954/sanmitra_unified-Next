from __future__ import annotations

from typing import Any


def tenant_has_module(tenant: dict[str, Any], module_key: str) -> bool:
    modules = {str(item or "").strip().lower() for item in (tenant.get("enabled_modules") or [])}
    return module_key in modules
