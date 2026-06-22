from enum import Enum
from typing import Iterable

from fastapi import Depends, HTTPException

from app.core.auth.dependencies import get_current_user


class Role(str, Enum):
    super_admin = "super_admin"
    tenant_admin = "tenant_admin"
    accountant = "accountant"
    operator = "operator"
    viewer = "viewer"
    ca_viewer = "ca_viewer"
    # HR / Payroll add-on (MitraBooks enterprise tier). Sensitive comp data is not
    # visible to tenant_admin by default — it must be granted one of these roles.
    hr_manager = "hr_manager"
    payroll_auditor = "payroll_auditor"
    employee_self = "employee_self"


def require_roles(allowed_roles: Iterable[Role]):
    allowed = {r.value for r in allowed_roles}

    async def _checker(current_user=Depends(get_current_user)):
        role = current_user.get("role")
        if role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return _checker
